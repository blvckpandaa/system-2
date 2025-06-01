
import os
import csv
import io
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Скачивает каталог ФККО со всех 455 страниц и сохраняет в data/fkko.csv"

    BASE_URL = "https://rpn.gov.ru/fkko/"
    PAGE_URL = "https://rpn.gov.ru/fkko/nav-more-fkko/page-{}/"

    def handle(self, *args, **options):
        all_rows = []

        try:
            for page in range(1, 456):  # от 1 до 455
                url = self.BASE_URL if page == 1 else self.PAGE_URL.format(page)
                self.stdout.write(f"Обработка страницы: {url}")
                try:
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    rows = soup.select('.registryCard__itemTableRow')
                    for item in rows:
                        if '_head' in (item.get('class') or []):
                            continue
                        code_div = item.select_one('.registryCard__itemTableCol._code')
                        name_link = item.select_one('.registryCard__itemTableCol._name a')
                        if code_div and name_link:
                            code = code_div.get_text(strip=True)
                            name = name_link.get_text(strip=True)
                            all_rows.append((code, name))
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"Ошибка на странице {page}: {e}"))
                    continue

            # Сохраняем в CSV
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(('code', 'name'))
            writer.writerows(all_rows)
            content = buf.getvalue().encode('utf-8')

            out_dir = os.path.join(os.getcwd(), 'data')
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, 'fkko.csv')
            with open(out_path, 'wb') as f:
                f.write(content)
            size = os.path.getsize(out_path)
            self.stdout.write(self.style.SUCCESS(f"Успешно сохранено {size} байт в {out_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Общая ошибка: {e}"))
