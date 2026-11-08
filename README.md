# Анализ рекламного A/B-теста

Сравнение конверсии пользователей, которым показывали рекламу, с контрольной группой PSA. Проект включает подготовку данных, статистическую проверку, SQL-запросы и краткий отчёт с результатами.

**Стек:** Python, pandas, SciPy, PostgreSQL, Jupyter, Matplotlib.

## Результат

В наборе 588 101 пользователь. Конверсия рекламной группы — **2,55%**, контрольной — **1,79%**. Абсолютная разница — **+0,77 процентного пункта**, 95% доверительный интервал — **от +0,59 до +0,94 п. п.** Относительная разница составляет около 43%.

![Сравнение конверсии двух групп](figures/conversion-comparison.png)

Это результат для исследуемого набора. Он не определяет окупаемость рекламы: данных о затратах и выручке в нём нет.

## Содержание

- Проверка пропусков, уникальности ID, типов и допустимых значений.
- Абсолютная и относительная разница конверсий, z-тест двух долей, интервал Newcombe–Wilson.
- Синтетическая A/A-проверка и оценка размера выборки для заданных MDE и мощности.
- Загрузка в PostgreSQL с проверками и контрольной суммой исходного файла.
- SQL с JOIN, группировками и оконными функциями.

## Материалы

| Материал | Где посмотреть |
|---|---|
| Ноутбук с анализом | [campaign-analysis.ipynb](notebooks/campaign-analysis.ipynb) |
| Выводы | [business-summary.md](results/business-summary.md) |
| Отчёт HTML | [dashboard.html](results/dashboard.html), скачать и открыть в браузере |
| SQL-запросы | [questions.sql](sql/questions.sql) |
| Расчёт и тесты | [src](src), [tests](tests) |

## Локальный запуск

Python 3.11+. Команды ниже приведены для PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/download_data.py --csv "путь/к/marketing_AB.csv"
python -m src.analysis
python -m unittest discover -s tests -v
```

Для автоматической загрузки исходного набора запустите `python scripts/download_data.py` без `--csv`. Для просмотра ноутбука — `jupyter lab`. CSV хранится локально в `data/raw/` и не включён в Git.

## PostgreSQL

```powershell
Copy-Item .env.example .env
# Задайте собственный пароль БД в .env.
docker compose up -d --wait
python -m src.database --init
python -m src.database
```

Docker использует локальный порт 55433. Для существующего PostgreSQL укажите реквизиты отдельной базы в `.env` и пропустите запуск контейнера. Таблицы: `campaign.loads`, `campaign.users`; представления для BI: `v_group_metrics`, `v_exposure_summary`.

## Ограничения

Одна строка соответствует одному пользователю. День и час относятся к показам, а не ко времени конверсии. Источник и метаданные набора сохранены в [data/source.json](data/source.json). Синтетическая A/A-проверка проверяет метод расчёта, а не качество исходной рандомизации.
