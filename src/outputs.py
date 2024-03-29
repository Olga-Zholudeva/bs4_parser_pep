import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import BASE_DIR, DATETIME_FORMAT


def control_output(results, cli_args):
    """Контроль действий, укзанных в командной строке."""

    output = cli_args.output
    outputs = {
        'pretty': pretty_output,
        None:  default_output
    }
    if output in outputs:
        outputs[output](results)
    else:
        file_output(results, cli_args)


def default_output(results):
    """Печатаем список results построчно."""

    for row in results:
        print(*row)


def pretty_output(results):
    """Вывод результата в терминал в табличной форме."""

    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    """Выгрузка результата в файл."""

    results_dir = BASE_DIR / 'results'
    results_dir.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    now_formatted = now.strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='unix')
        writer.writerows(results)
    logging.info(f'Файл с результатами был сохранён: {file_path}')
