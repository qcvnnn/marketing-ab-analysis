"""Run the analysis and write reproducible aggregates, figures and a business note."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .data import ROOT, load_data
from .statistics import compare, wilson, required_sample, aa_simulation


def analyze(frame):
    groups=frame.groupby('test_group').converted.agg(users='size',conversions='sum').reindex(['psa','ad'])
    groups['conversion_rate']=groups.conversions/groups.users
    intervals=[wilson(int(r.conversions),int(r.users)) for r in groups.itertuples()]
    groups['ci_low']=[x[0] for x in intervals]; groups['ci_high']=[x[1] for x in intervals]
    control=groups.loc['psa']; test=groups.loc['ad']
    effect=compare(int(control.conversions),int(control.users),int(test.conversions),int(test.users))
    return groups,effect


def run():
    results=ROOT/'results'; figures=ROOT/'figures'
    results.mkdir(exist_ok=True); figures.mkdir(exist_ok=True)
    frame,quality=load_data()
    groups,effect=analyze(frame)
    groups.to_csv(results/'group_metrics.csv',index_label='test_group')
    quality.update({'validated_rows':len(frame),'duplicate_user_ids':int(frame.user_id.duplicated().sum()),
                    'missing_values':frame.isna().sum().to_dict(),'max_total_ads':int(frame.total_ads.max()),
                    'transformations':['Removed verified sequential CSV export index; normalized column names and booleans.'],
                    'excluded_rows':0})
    day=frame.groupby(['most_ads_day','test_group']).converted.agg(users='size',conversions='sum').reset_index()
    day['conversion_rate']=day.conversions/day.users
    day.to_csv(results/'exposure_day_descriptive.csv',index=False)
    ratio=float(groups.loc['ad','users']/groups.loc['psa','users'])
    planning=[required_sample(),required_sample(ratio=ratio)]
    aa,pvalues=aa_simulation()
    payload={'quality':quality,'effect':effect,'observed_test_to_control_ratio':ratio,
             'groups':groups.reset_index().to_dict(orient='records'),
             'future_planning_scenarios':planning,'aa_simulation':aa,
             'limits':['Historical group allocation and randomization protocol are not independently verified.',
                       'No calendar timeline, revenue, costs or pre-treatment covariates.',
                       'Exposure-derived attributes are post-treatment/descriptive, not causal segments.',
                       'No SRM claim: intended allocation ratio was not documented.']}
    (results/'analysis.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    x=np.arange(2); rates=100*groups.conversion_rate.to_numpy()
    errors=np.array([100*(groups.conversion_rate-groups.ci_low),100*(groups.ci_high-groups.conversion_rate)])
    ax[0].bar(x,rates,color=['#a8b6c5','#267a84'],width=.55)
    ax[0].errorbar(x,rates,yerr=errors,fmt='none',ecolor='#173042',capsize=5)
    ax[0].set(xticks=x,xticklabels=['PSA — контроль','Реклама'],ylabel='Конверсия, %',title='Доли покупок и 95% интервалы')
    ax[0].set_ylim(0,max(rates)*1.3)
    for i,(label,row) in enumerate(groups.iterrows()):
        ax[0].text(i,rates[i]+.16,f'{rates[i]:.2f}%\nn = {int(row.users):,}'.replace(',',' '),ha='center',fontsize=10)
    ax[1].errorbar([100*effect['difference']],[0],xerr=[[100*(effect['difference']-effect['ci_low'])],[100*(effect['ci_high']-effect['difference'])]],fmt='o',color='#267a84',capsize=6)
    ax[1].axvline(0,color='#9b4747',ls='--',lw=1)
    ax[1].set(yticks=[],xlabel='Разница конверсий, процентные пункты',title='Реклама минус PSA · 95% интервал')
    ax[1].set_xlim(min(-.1,100*effect['ci_low']-.1),100*effect['ci_high']+.15)
    fig.savefig(figures/'conversion-comparison.png',dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.5),layout='constrained')
    ax.hist(pvalues,bins=np.linspace(0,1,21),color='#267a84',edgecolor='white')
    ax.axvline(.05,color='#9b4747',ls='--',label='α = 0,05')
    ax.set(xlabel='p-value',ylabel='Число симуляций',title='Проверка теста на искусственных A/A-данных')
    ax.legend(); fig.savefig(figures/'aa-calibration.png',dpi=150); plt.close(fig)

    note=f'''# Что показало сравнение рекламных групп

В данных {len(frame):,} пользователей. В группе рекламы доля покупок — {100*effect['test_rate']:.2f}%, в PSA — {100*effect['control_rate']:.2f}%. Разница составляет **{100*effect['difference']:.2f} процентного пункта**, или около **{100*effect['relative_lift']:.1f}% относительно контроля**.

95% доверительный интервал разницы: {100*effect['ci_low']:.2f}–{100*effect['ci_high']:.2f} п.п. Двусторонний z-тест: p = {effect['p_value']:.3g}. Это несовместимо с равными конверсиями при предпосылках теста. Размер различия и его неопределённость важнее одной отметки «значимо».

## Решение для бизнеса

Результат поддерживает дальнейшую проверку рекламной коммуникации. Он не даёт достаточных оснований сразу масштабировать кампанию: неизвестны стоимость рекламы, маржа, окно наблюдения и подтверждённый протокол назначения групп. Рассчитать прибыль и ROI из этого файла нельзя.

До запуска нового эксперимента нужно согласовать единицу рандомизации (пользователь), конверсию как основную метрику, окно наблюдения, MDE, пропорцию групп и защитные метрики, например отписки и жалобы. Последние метрики в исходном CSV отсутствуют.

## Что нельзя заключать

- Группа рекламы существенно больше контроля. Без плановой пропорции нельзя объявлять это ошибкой распределения (SRM).
- Наибольший объём показов по дню/часу не равен дате покупки или времени назначения группы. Календарного временного ряда здесь нет.
- Число показов может зависеть от воздействия. По нему нельзя без дополнительных предпосылок выбирать клиентов или утверждать, что увеличение частоты показов вызывает рост покупок.
- Происхождение данных и рандомизация не подтверждены первичным протоколом. Поэтому основной вывод — различие в опубликованных группах; причинная интерпретация условна.

## План следующего теста

Иллюстративные параметры: базовая конверсия 2%, MDE +0,5 п.п., мощность 80%, α = 0,05. При равных группах нормальная аппроксимация даёт {planning[0]['control_users']:,} пользователей в каждой группе. Это отдельный сценарий будущего эксперимента, а не расчёт «достигнутой мощности» текущего теста.

В {aa['repeats']:,} искусственных A/A-симуляций доля ложных отклонений составила {100*aa['false_positive_rate']:.2f}%. Это проверка реализации на модели данных, не доказательство корректной рандомизации исходного набора.
'''
    (results/'business-summary.md').write_text(note,encoding='utf-8')
    build_dashboard(payload)
    print(json.dumps({'rows':len(frame),'effect':effect,'planning':planning,'aa_false_positive_rate':aa['false_positive_rate']},ensure_ascii=False,indent=2))
    return payload


def build_dashboard(payload):
    """A self-contained local report; no external scripts or data transmission."""
    e=payload['effect']; groups=payload['groups']
    rows=''.join(f'<tr><td>{r["test_group"]}</td><td>{r["users"]:,}</td><td>{r["conversions"]:,}</td><td>{100*r["conversion_rate"]:.2f}%</td></tr>' for r in groups)
    content=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Работает ли рекламная коммуникация?</title><style>body{{font:17px/1.6 system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 24px;color:#22313e;background:#fafbf9}}h1{{font-size:36px;line-height:1.2}}h2{{margin-top:36px}}.muted{{color:#526572}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #d7e1e5}}img{{width:100%;height:auto}}.metric{{font-size:38px;color:#236c74;font-weight:700}}a{{color:#236c74}}</style>
<p class="muted">Учебный проект · Python · PostgreSQL · статистика</p><h1>Работает ли рекламная коммуникация?</h1>
<p>Сравнение долей покупок в группах рекламы и нейтральных объявлений PSA.</p>
<p class="metric">+{100*e['difference']:.2f} п.п.</p><p>Наблюдаемая разница конверсии; 95% интервал {100*e['ci_low']:.2f}–{100*e['ci_high']:.2f} п.п.</p>
<table><thead><tr><th>Группа</th><th>Пользователи</th><th>Покупки</th><th>Конверсия</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Размер различия</h2><img src="../figures/conversion-comparison.png" alt="Конверсии групп и доверительный интервал их разницы">
<h2>Что делать бизнесу</h2><p>Проверить стоимость контакта и маржинальность, подтвердить протокол распределения и провести следующий контролируемый тест. Значимость различия не означает автоматически прибыльность кампании.</p>
<h2>Что ограничивает вывод</h2><p>Нет расходов, выручки, предэкспериментальных характеристик и календарных дат. Плановая доля групп и исходный протокол рандомизации не подтверждены. Дни/часы максимального количества показов используются только описательно.</p>
<h2>Проверка статистического кода</h2><img src="../figures/aa-calibration.png" alt="Распределение p-value при искусственных одинаковых группах">
<p class="muted">График основан на синтетических A/A-симуляциях. Это отдельная проверка метода.</p>
<p><a href="business-summary.md">Полный вывод</a> · <a href="analysis.json">Числа и параметры</a> · <a href="../README.md">Описание проекта</a></p></html>'''
    (ROOT/'results/dashboard.html').write_text(content,encoding='utf-8')


if __name__=='__main__':
    run()
