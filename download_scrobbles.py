# download_scrobbles_debug.py
import time
import requests
from playwright.sync_api import sync_playwright
import os
from datetime import datetime

DATA_PATH = "data/scrobbles.csv"
URL = "https://benjaminbenben.com/lastfm-to-csv/"

def download_csv_debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # <- abrir navegador visible
        page = browser.new_page()
        page.goto(URL)

        save_button = page.locator("a.btn.btn-info").filter(has_text="Save")

        # =========================
        # Calcular tiempo máximo de espera
        # =========================
        start_date = datetime(2025, 5, 1)
        now = datetime.now()
        months = (now.year - start_date.year) * 12 + (now.month - start_date.month) + 1
        max_wait_seconds = months * 2.5  # 2,5 segundos por mes

        print(f"Esperando hasta {max_wait_seconds:.1f}s para que el CSV esté listo...")

        csv_url = None
        interval = 0.5
        last_text = ""
        for i in range(int(max_wait_seconds / interval)):
            try:
                text = save_button.text_content().strip()
                href = save_button.get_attribute("href")
                if text != last_text:
                    print(f"[{i*interval:.1f}s] Botón text: '{text}', href: '{href}'")
                    last_text = text
                if href and not href.startswith("#") and "0 KB" not in text:
                    csv_url = href
                    print(f"CSV listo en: {csv_url}")
                    break
            except Exception as e:
                print(f"Error leyendo botón: {e}")
            time.sleep(interval)

        if not csv_url:
            raise Exception(
                f"El CSV aún no está listo o no se pudo obtener el enlace "
                f"(esperado máximo {max_wait_seconds:.1f}s)."
            )

        response = requests.get(csv_url)
        response.raise_for_status()
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "wb") as f:
            f.write(response.content)

        print(f"CSV descargado correctamente en {DATA_PATH}")
        browser.close()


if __name__ == "__main__":
    download_csv_debug()