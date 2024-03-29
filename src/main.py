import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP_URL
from exceptions import ParserLastVersionExeption
from outputs import control_output
from utils import find_tag, get_response


def whats_new(session):
    """Парсинг данных о нововведениях в Python."""

    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        verversion_a_tag = section.find('a')
        href = verversion_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )
    return results


def latest_versions(session):
    """Парсинг данных о версиях Python."""

    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise ParserLastVersionExeption('Ничего не нашлось')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        version, status = text_match.groups() if text_match else a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    """Скачивание файлов."""

    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    table_tag = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag, 'a', attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    """Парсинг документации PEP."""

    response = session.get(PEP_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_table = soup.find('section', id='numerical-index')
    all_peps = main_table.find_all('tr')
    statuses = defaultdict(int)
    results = [('Статус', 'Количество')]
    for side in tqdm(all_peps[1:]):
        status_main_page = side.find('abbr').text[1:]
        pep = side.find('a')['href']
        response = session.get(urljoin(PEP_URL, pep))
        if response is None:
            return
        soup = BeautifulSoup(response.text, 'lxml')
        status_on_the_page = soup.find('abbr').text
        if (
            status_on_the_page not in EXPECTED_STATUS[status_main_page]
        ):
            logging.info(
                'Несовпадающие статусы:''\n'
                f'{urljoin(PEP_URL, pep)}''\n'
                f'Статус в карточке: {status_on_the_page}''\n'
                f'Ожидаемые статусы: {EXPECTED_STATUS[status_main_page]}''\n'
            )
        statuses[status_on_the_page] += 1
    for key, value in statuses.items():
        record = (key, value)
        results.append(record)
    total = sum(statuses.values())
    results.append(('Total', total))
    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
