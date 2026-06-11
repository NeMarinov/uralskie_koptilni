import requests
from bs4 import BeautifulSoup

BASE_URL = "https://уральские-коптильни.рф"
CATALOG_URL = f"{BASE_URL}/katalog/koptilni/"

def _get_blocks():
    response = requests.get(CATALOG_URL).text
    soup = BeautifulSoup(response, "lxml")
    return soup.find_all('div', class_='col-6 col-lg-3')

def get_count():
    blocks = _get_blocks()
    count = 0
    for block in blocks:
        name_tag = block.find('div', class_='catalog-list__item-name')
        if name_tag and name_tag.text.strip():
            count += 1
    return count

def first_find_function_kopt(index):
    blocks = _get_blocks()
    result = {}
    block = blocks[index]

    name_tag = block.find('div', class_='catalog-list__item-name')
    result["name"] = name_tag.text.strip() if name_tag else None

    price_tag = block.find('div', class_='catalog-list__item-price')
    result["price"] = price_tag.text.strip() if price_tag else None

    link_tag = block.find('a')
    result["link"] = link_tag['href'] if link_tag else None

    img_tag = block.find('img')
    result["image"] = img_tag['src'] if img_tag else None

    return result

def second_find_function_kopt(index):
    blocks = _get_blocks()
    result = {}
    block = blocks[index]

    link_tag = block.find('a')
    url_next_page = link_tag['href'] if link_tag else None

    if not url_next_page:
        return None

    response_n_page = requests.get(f"{BASE_URL}{url_next_page}")
    soup1 = BeautifulSoup(response_n_page.text, 'lxml')

    block_n_page = soup1.find_all('div', class_="col-6 col-lg-6")
    all_names = soup1.find_all('div', class_="catalog-detail__complect-item-name")
    result['count'] = len(all_names)

    for idx, item in enumerate(block_n_page, start=1):
        name_tag = item.find('div', class_="catalog-detail__complect-item-name")
        count_tag = item.find('div', class_="catalog-detail__complect-item-count")

        result[f'name_{idx}'] = name_tag.text.strip() if name_tag else None
        result[f'count_{idx}'] = count_tag.text.strip() if count_tag else None

    return result

def third_find_function_additionally(index):
    blocks = _get_blocks()
    result = {}
    block = blocks[index]

    link_tag = block.find('a')
    url_next_page = link_tag['href'] if link_tag else None

    if not url_next_page:
        return None

    response_next_page = requests.get(f"{BASE_URL}{url_next_page}")
    soup1 = BeautifulSoup(response_next_page.text, 'lxml')

    block_next_page = soup1.find_all('div', class_="catalog-detail__more-complect-item")

    for ind, item in enumerate(block_next_page, start=1):
        name_tag = item.find('div', class_="catalog-detail__more-complect-name")
        price_tag = item.find('div', class_="catalog-detail__more-complect-price")

        result[f'name_{ind}'] = name_tag.text.strip() if name_tag else None
        result[f'price_{ind}'] = price_tag.text.strip() if price_tag else None

    return result