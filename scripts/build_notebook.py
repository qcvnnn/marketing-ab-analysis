"""Build and execute a small explanatory notebook from the project's own functions."""
from pathlib import Path
import sys
import nbformat as nbf
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'notebooks'; folder.mkdir(exist_ok=True)
md=nbf.v4.new_markdown_cell; code=nbf.v4.new_code_cell
nb=nbf.v4.new_notebook(cells=[
md('''# Помогает ли реклама получать больше покупок?

Учебный анализ Marketing A/B Testing с Kaggle. Одна строка — один пользователь. Сравниваем опубликованные группы `ad` и `psa`, считаем размер различия и неопределённость, затем формулируем следующий шаг для бизнеса.

Первичный протокол рандомизации, окно наблюдения и расходы отсутствуют. Поэтому вывод о причинном эффекте условен, а ROI не рассчитывается. Используется локальный файл `marketing_AB.csv`; подготовить его можно командой `python scripts/download_data.py --csv "путь/к/marketing_AB.csv"`.'''),
code('''from pathlib import Path
import sys
ROOT = Path.cwd()
if not (ROOT / 'src').exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
from src.data import load_data
from src.analysis import analyze
from src.statistics import required_sample, aa_simulation
import pandas as pd
from IPython.display import display, Image
frame, quality = load_data()
print(f'Пользователей: {len(frame):,}')
print('Колонки:', ', '.join(frame.columns))
print('Пропусков:', int(frame.isna().sum().sum()))
print('Повторяющихся ID:', int(frame.user_id.duplicated().sum()))'''),
md('''## Что будем измерять

Бизнес-вопрос: отличается ли вероятность покупки у пользователей рекламной группы от PSA? Основная метрика — число пользователей с `converted=True`, делённое на число пользователей группы. Одна строка не является одним рекламным показом.

H₀: конверсии равны. Альтернатива двусторонняя. α = 0,05. Анализ ретроспективный; это не зарегистрированный до запуска протокол эксперимента. Дни и часы показов не используются для поиска «значимого сегмента».'''),
code('''groups, effect = analyze(frame)
display(groups)
print(f"Разница: {effect['difference']*100:.3f} п.п.")
print(f"Относительное различие: {effect['relative_lift']*100:.2f}%")
print(f"95% интервал: [{effect['ci_low']*100:.3f}; {effect['ci_high']*100:.3f}] п.п.")
print(f"p-value: {effect['p_value']:.3g}")'''),
md('''## Как читать результат

Процентный пункт — разность процентов; относительный рост — отношение этой разности к контрольной конверсии. Это разные величины.

Для сравнения используем z-тест двух долей. Для интервала разницы — метод Newcombe на основе интервалов Wilson. Наблюдений и успешных исходов достаточно для нормальной аппроксимации; предположение о независимости и назначении групп нужно подтвердить по первичным документам.

`p-value` не является вероятностью истинности H₀. 95% доверительный интервал описывает процедуру оценивания при повторении, а не вероятность попадания уже фиксированного параметра в конкретный интервал.'''),
code("display(Image(filename=str(ROOT/'figures/conversion-comparison.png')))"),
md('''## Проверка статистического метода

Генерируем искусственные группы с одинаковой вероятностью покупки. Проверяем, как часто тест ошибочно находит отличие. Это симуляция для проверки кода, не A/A-эксперимент над исходными пользователями.'''),
code('''aa, _ = aa_simulation()
display(pd.DataFrame([aa]).drop(columns=['note']))
display(Image(filename=str(ROOT/'figures/aa-calibration.png')))'''),
md('''## Планирование следующего эксперимента

Отдельный иллюстративный сценарий: базовая конверсия 2%, минимальный интересующий эффект +0,5 п.п., мощность 80%. Это допущения для будущего теста, не «наблюдаемая мощность» текущего. Сравним равное распределение с соотношением размеров групп в опубликованном наборе.'''),
code('''ratio = groups.loc['ad', 'users'] / groups.loc['psa', 'users']
display(pd.DataFrame([required_sample(), required_sample(ratio=float(ratio))]).drop(columns=['note']))'''),
md('''## Вывод для бизнеса

В опубликованных группах есть положительное различие конверсии. Масштабирование нельзя обосновать одним p-value: нужны стоимость контакта, маржа, подтверждение распределения и защитные метрики. Предлагаемый следующий шаг — контролируемый тест с заранее зафиксированным дизайном.

Не строим причинные выводы о частоте показов и времени суток: эти характеристики могли возникнуть после воздействия. Не называем разницу размеров групп SRM без известной плановой пропорции. Не применяем CUPED без предэкспериментальных данных.

Подробный вывод: `results/business-summary.md`. SQL и оконные функции: `sql/questions.sql`. Проверки: `python -m unittest discover -s tests -v`.''')])
nb.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'}
nb.metadata['language_info']={'name':'python','version':sys.version.split()[0]}
manager=KernelManager(kernel_name='python3')
manager.kernel_spec.argv[0]=sys.executable
client=NotebookClient(nb,km=manager,timeout=180,resources={'metadata':{'path':str(ROOT)}})
try:
    client.execute()
finally:
    if manager.has_kernel: manager.shutdown_kernel(now=True)
path=folder/'campaign-analysis.ipynb'; nbf.write(nb,path)
assert not any(output.output_type=='error' for cell in nb.cells if cell.cell_type=='code' for output in cell.get('outputs',[]))
print('Executed notebook:',path)
