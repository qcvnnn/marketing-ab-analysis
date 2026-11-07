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
md('# Помогает ли реклама получать больше покупок?\n\nСравнение конверсий групп `ad` и `psa` по данным Marketing A/B Testing. Одна строка — один пользователь.\n\nПодготовить CSV: `python scripts/download_data.py --csv "путь/к/marketing_AB.csv"`.'),
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
md('## Метрика и гипотеза\n\nКонверсия = пользователи с покупкой / все пользователи группы.\n\nH₀: конверсии равны. Альтернатива двусторонняя, α = 0,05.'),
code('''groups, effect = analyze(frame)
display(groups)
print(f"Разница: {effect['difference']*100:.3f} п.п.")
print(f"Относительное различие: {effect['relative_lift']*100:.2f}%")
print(f"95% интервал: [{effect['ci_low']*100:.3f}; {effect['ci_high']*100:.3f}] п.п.")
print(f"p-value: {effect['p_value']:.3g}")'''),
md('## Метод\n\nСравнение двух долей — z-тест. Интервал разницы — Newcombe–Wilson. Абсолютная разница измеряется в процентных пунктах, относительная — в процентах от контроля.'),
code("display(Image(filename=str(ROOT/'figures/conversion-comparison.png')))"),
md('## A/A-симуляция\n\nИскусственные группы с одинаковой вероятностью покупки. Оценка частоты ложных отклонений H₀.'),
code('''aa, _ = aa_simulation()
display(pd.DataFrame([aa]).drop(columns=['note']))
display(Image(filename=str(ROOT/'figures/aa-calibration.png')))'''),
md('## Размер будущего теста\n\nПараметры примера: базовая конверсия 2%, MDE +0,5 п.п., мощность 80%, α = 0,05. Сравнить равные группы и пропорцию текущего набора.'),
code('''ratio = groups.loc['ad', 'users'] / groups.loc['psa', 'users']
display(pd.DataFrame([required_sample(), required_sample(ratio=float(ratio))]).drop(columns=['note']))'''),
md('## Вывод\n\nВ группе рекламы наблюдается более высокая конверсия. Для решения о масштабировании нужны данные о затратах, маржинальности и подтверждённом дизайне эксперимента. Дни, часы и количество показов используются описательно.\n\nРезультаты — `results/business-summary.md`, SQL — `sql/questions.sql`.')])
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
