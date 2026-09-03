import json
import os
import urllib.parse
from datetime import datetime, timedelta
import requests
import streamlit as st

# Plik bazy danych
PLIK_ZLECEN = "zlecenia.json"


# Funkcje do zapisu i odczytu danych
def wczytaj_zlecenia():
    if os.path.exists(PLIK_ZLECEN):
        try:
            with open(PLIK_ZLECEN, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def zapisz_zlecenia(zlecenia):
    with open(PLIK_ZLECEN, "w", encoding="utf-8") as f:
        json.dump(zlecenia, f, ensure_ascii=False, indent=4)


def usun_zlecenie(id_zlecenia):
    st.session_state.zlecenia = [
        z for z in st.session_state.zlecenia if z["id_zlecenia"] != id_zlecenia
    ]
    zapisz_zlecenia(st.session_state.zlecenia)
    st.rerun()


# Konfiguracja floty wg kierowców i pojemności
FLOTA = [
    {"id": 1, "kierowca": "Przemek", "pojemnosc": 9},
    {"id": 2, "kierowca": "Dudek", "pojemnosc": 9},
    {"id": 3, "kierowca": "Tymek", "pojemnosc": 9},
    {"id": 4, "kierowca": "Andrzej", "pojemnosc": 9},
    {"id": 5, "kierowca": "Adam", "pojemnosc": 7},
    {"id": 6, "kierowca": "Darek", "pojemnosc": 6},
]

OPCJE_ZRODLA = [
    "ClickTrans",
    "Klient stały",
    "Giełda Trans.eu",
    "Otomoto / Telefon",
    "Inne",
]


def znajdz_najblizszy_wtorek(data_start):
    dni_do_wtorku = (1 - data_start.weekday()) % 7
    return data_start + timedelta(days=dni_do_wtorku)


def oblicz_kilometry(skad, dokad):
    try:
        r1 = requests.get(
            f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(skad)}",
            headers={"User-Agent": "AutotransportApp"},
        ).json()
        r2 = requests.get(
            f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(dokad)}",
            headers={"User-Agent": "AutotransportApp"},
        ).json()

        if r1 and r2:
            lon1, lat1 = r1[0]["lon"], r1[0]["lat"]
            lon2, lat2 = r2[0]["lon"], r2[0]["lat"]

            route_url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
            route_res = requests.get(route_url).json()

            if "routes" in route_res and len(route_res["routes"]) > 0:
                dystans_km = route_res["routes"][0]["distance"] / 1000
                czas_h = route_res["routes"][0]["duration"] / 3600
                return round(dystans_km, 1), round(czas_h, 1)
    except Exception:
        pass
    return None, None


# Inicjalizacja zleceń z pliku
if "zlecenia" not in st.session_state:
    st.session_state.zlecenia = wczytaj_zlecenia()

# Inicjalizacja przesunięcia tygodni w nawigacji
if "tydzien_offset" not in st.session_state:
    st.session_state.tydzien_offset = 0

st.set_page_config(page_title="AmmaCars - System Spedycji", layout="wide")

# Wyświetlanie Logo na samej górze
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=180)
with col_title:
    st.title("Panel Spedytora - Transport Aut (Polska ⇄ Hiszpania)")

opcje_kierowcow = ["Automatyczny dobór", "Brak (Tylko do harmonogramu)"] + [
    f"{c['kierowca']} ({c['pojemnosc']} aut)" for c in FLOTA
]

# Menu boczne z formularzem
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

st.sidebar.header("➕ Dodaj Nowe Zlecenie")

with st.sidebar.form(key="form_dodaj_zlecenie", clear_on_submit=False):
    kierunek = st.radio(
        "Kierunek trasy",
        ["Polska -> Hiszpania (Wyjazd)", "Hiszpania -> Polska (Powrót)"],
    )
    wybrany_kierowca_opcja = st.selectbox("Wybierz kierowcę", opcje_kierowcow)
    marka_model = st.text_input("Marka i Model pojazdu", "BMW X5")

    # POLE: Źródło zlecenia
    zrodlo_wybor = st.selectbox("Źródło zlecenia", OPCJE_ZRODLA)
    if zrodlo_wybor == "Inne":
        zrodlo = st.text_input("Wpisz własne źródło", "Inne giełdy")
    else:
        zrodlo = zrodlo_wybor

    if "Polska" in kierunek.split("->")[0]:
        domyslne_skad = "Warszawa, Poland"
        domyslne_dokad = "Malaga, Spain"
    else:
        domyslne_skad = "Malaga, Spain"
        domyslne_dokad = "Warszawa, Poland"

    skad = st.text_input("Miejsce załadunku (Skąd)", domyslne_skad)
    dokad = st.text_input("Miejsce rozładunku (Dokąd)", domyslne_dokad)
    ilosc_aut = st.number_input(
        "Liczba aut (szt.)", min_value=1, max_value=9, value=1
    )
    cena = st.number_input(
        "Cena za zlecenie (EUR)", min_value=0, value=1300, step=50
    )
    data_gotowosci = st.date_input(
        "Data gotowości ładunku", datetime.now().date()
    )

    btn_submit = st.form_submit_button("➕ Dodaj / Przypisz Zlecenie")

# --- NAWIGACJA TYGODNIAMI ---
baza_data = (
    znajdz_najblizszy_wtorek(data_gotowosci)
    if btn_submit
    else znajdz_najblizszy_wtorek(datetime.now().date())
)
data_wyjazdu = baza_data + timedelta(weeks=st.session_state.tydzien_offset)
data_wyjazdu_str = data_wyjazdu.strftime("%Y-%m-%d")

# Pasek nawigacji po tygodniach
st.markdown("---")
c_nav1, c_nav2, c_nav3, c_nav4 = st.columns([1, 1, 3, 1])
with c_nav1:
    if st.button("◀ Poprzedni tydzień"):
        st.session_state.tydzien_offset -= 1
        st.rerun()
with c_nav2:
    if st.button("Dziś"):
        st.session_state.tydzien_offset = 0
        st.rerun()
with c_nav4:
    if st.button("Następny tydzień ▶"):
        st.session_state.tydzien_offset += 1
        st.rerun()
with c_nav3:
    st.markdown(
        f"<h3 style='text-align: center; margin:0;'>🗓️ Tydzień wyjazdowy:"
        f" {data_wyjazdu_str}</h3>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# --- PODSUMOWANIE FINANSOWE / KPI ---
zlecenia_biezace = [
    z
    for z in st.session_state.zlecenia
    if z["data_wyjazdu"] == data_wyjazdu_str and z["ciężarówka_id"] is not None
]

przychod_tydzien = sum(z.get("cena", 0) for z in zlecenia_biezace)
auta_tydzien = sum(z.get("ilosc_aut", 0) for z in zlecenia_biezace)
srednia_auto = round(przychod_tydzien / auta_tydzien, 1) if auta_tydzien > 0 else 0

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("💰 Przychód w tym tygodniu", f"{przychod_tydzien} EUR")
kpi2.metric("🚘 Załadowane auta (Flota)", f"{auta_tydzien} szt.")
kpi3.metric("📊 Średnia stawka za auto", f"{srednia_auto} EUR")

# --- PODGLĄD FLOTY NA STRONIE GŁÓWNEJ ---
st.subheader(f"🚛 Stan Floty na tydzień startujący: Wtorek, {data_wyjazdu_str}")

zajete_wyjazd = {c["id"]: 0 for c in FLOTA}
zajete_powrot = {c["id"]: 0 for c in FLOTA}

for z in zlecenia_biezace:
    if z["typ_trasy"] == "Wyjazd":
        zajete_wyjazd[z["ciężarówka_id"]] += z["ilosc_aut"]
    else:
        zajete_powrot[z["ciężarówka_id"]] += z["ilosc_aut"]

cols = st.columns(3)
for idx, c in enumerate(FLOTA):
    col = cols[idx % 3]

    z_wyjazd = zajete_wyjazd[c["id"]]
    w_wyjazd = c["pojemnosc"] - z_wyjazd

    z_powrot = zajete_powrot[c["id"]]
    w_powrot = c["pojemnosc"] - z_powrot

    ladunki_wyjazd_kierowcy = [
        z
        for z in zlecenia_biezace
        if z["ciężarówka_id"] == c["id"] and z["typ_trasy"] == "Wyjazd"
    ]
    ladunki_powrot_kierowcy = [
        z
        for z in zlecenia_biezace
        if z["ciężarówka_id"] == c["id"] and z["typ_trasy"] == "Powrót"
    ]

    with col:
        with st.container(border=True):
            st.markdown(
                f"### 🚚 {c['kierowca']} <small style='color:gray; font-size:"
                f" 0.9rem;'>(Max: {c['pojemnosc']} aut)</small>",
                unsafe_allow_html=True,
            )

            c_wyj, c_pow = st.columns(2)
            with c_wyj:
                st.markdown("**📤 WYJAZD (PL➔ES)**")
                st.write(f"Zajęte: **{z_wyjazd}** | Wolne: **{w_wyjazd}**")
                if w_wyjazd == 0:
                    st.error("🔴 Pełny")
                else:
                    st.success(f"🟢 Wolne: {w_wyjazd}")

                if ladunki_wyjazd_kierowcy:
                    st.markdown("**📋 Ładunki:**")
                    for l in ladunki_wyjazd_kierowcy:
                        col_text, col_btn = st.columns([5, 1])
                        with col_text:
                            skad_miasto = l["skad"].split(",")[0]
                            dokad_miasto = l["dokad"].split(",")[0]
                            zrodlo_txt = l.get("zrodlo", "Brak źródła")
                            st.markdown(
                                f"<div style='margin-bottom: 8px; font-size:"
                                " 1.05rem; line-height: 1.3;'>"
                                f"• <b>{l['ilosc_aut']}x {l['marka_model']}</b>"
                                f" <span style='color:#2e7d32;"
                                f" font-weight:bold;'>({l['cena']}€)</span><br>"
                                f"&nbsp;&nbsp;&nbsp;📍 <b>{skad_miasto} ➔"
                                f" {dokad_miasto}</b><br>"
                                f"&nbsp;&nbsp;&nbsp;<small"
                                " style='background-color:#e0f2fe;"
                                " color:#0369a1; padding:2px 6px;"
                                f" border-radius:4px;'>🏷️ {zrodlo_txt}</small>"
                                "</div>",
                                unsafe_allow_html=True,
                            )
                        with col_btn:
                            if st.button(
                                "🗑️",
                                key=f"del_card_w_{l['id_zlecenia']}",
                                help="Usuń zlecenie",
                            ):
                                usun_zlecenie(l["id_zlecenia"])

            with c_pow:
                st.markdown("**📥 POWRÓT (ES➔PL)**")
                st.write(f"Zajęte: **{z_powrot}** | Wolne: **{w_powrot}**")
                if w_powrot == 0:
                    st.error("🔴 Pełny")
                else:
                    st.success(f"🟢 Wolne: {w_powrot}")

                if ladunki_powrot_kierowcy:
                    st.markdown("**📋 Ładunki:**")
                    for l in ladunki_powrot_kierowcy:
                        col_text, col_btn = st.columns([5, 1])
                        with col_text:
                            skad_miasto = l["skad"].split(",")[0]
                            dokad_miasto = l["dokad"].split(",")[0]
                            zrodlo_txt = l.get("zrodlo", "Brak źródła")
                            st.markdown(
                                f"<div style='margin-bottom: 8px; font-size:"
                                " 1.05rem; line-height: 1.3;'>"
                                f"• <b>{l['ilosc_aut']}x {l['marka_model']}</b>"
                                f" <span style='color:#2e7d32;"
                                f" font-weight:bold;'>({l['cena']}€)</span><br>"
                                f"&nbsp;&nbsp;&nbsp;📍 <b>{skad_miasto} ➔"
                                f" {dokad_miasto}</b><br>"
                                f"&nbsp;&nbsp;&nbsp;<small"
                                " style='background-color:#e0f2fe;"
                                " color:#0369a1; padding:2px 6px;"
                                f" border-radius:4px;'>🏷️ {zrodlo_txt}</small>"
                                "</div>",
                                unsafe_allow_html=True,
                            )
                        with col_btn:
                            if st.button(
                                "🗑️",
                                key=f"del_card_p_{l['id_zlecenia']}",
                                help="Usuń zlecenie",
                            ):
                                usun_zlecenie(l["id_zlecenia"])

st.divider()

typ_trasy_aktualnej = (
    "Wyjazd" if "Polska -> Hiszpania" in kierunek else "Powrót"
)

# --- LOGIKA OBSŁUGI DODAWANIA ZLECENIA ---
if btn_submit:
    km, czas = oblicz_kilometry(skad, dokad)

    if wybrany_kierowca_opcja == "Brak (Tylko do harmonogramu)":
        st.session_state.zlecenia.append({
            "id_zlecenia": datetime.now().timestamp(),
            "data_wyjazdu": data_wyjazdu_str,
            "ciężarówka_id": None,
            "kierowca": "Nieprzypisany",
            "typ_trasy": typ_trasy_aktualnej,
            "marka_model": marka_model,
            "zrodlo": zrodlo,
            "skad": skad,
            "dokad": dokad,
            "ilosc_aut": ilosc_aut,
            "cena": cena,
            "km": km,
        })
        zapisz_zlecenia(st.session_state.zlecenia)
        st.success(
            f"✅ Dodano zlecenie ({ilosc_aut}x {marka_model} - źródło: {zrodlo})"
            " do harmonogramu!"
        )
        st.rerun()

    elif wybrany_kierowca_opcja != "Automatyczny dobór":
        imie_kierowcy = wybrany_kierowca_opcja.split(" ")[0]
        ciężarówka = next(c for c in FLOTA if c["kierowca"] == imie_kierowcy)

        miejsca_zajete = (
            zajete_wyjazd[ciężarówka["id"]]
            if typ_trasy_aktualnej == "Wyjazd"
            else zajete_powrot[ciężarówka["id"]]
        )
        wolne = ciężarówka["pojemnosc"] - miejsca_zajete

        if wolne >= ilosc_aut:
            st.session_state.zlecenia.append({
                "id_zlecenia": datetime.now().timestamp(),
                "data_wyjazdu": data_wyjazdu_str,
                "ciężarówka_id": ciężarówka["id"],
                "kierowca": ciężarówka["kierowca"],
                "typ_trasy": typ_trasy_aktualnej,
                "marka_model": marka_model,
                "zrodlo": zrodlo,
                "skad": skad,
                "dokad": dokad,
                "ilosc_aut": ilosc_aut,
                "cena": cena,
                "km": km,
            })
            zapisz_zlecenia(st.session_state.zlecenia)
            st.success(
                f"✅ Dodano zlecenie ({ilosc_aut}x {marka_model}) dla kierowcy:"
                f" **{ciężarówka['kierowca']}**!"
            )
            st.rerun()
        else:
            st.error(
                f"❌ Kierowca {ciężarówka['kierowca']} nie ma wystarczająco"
                f" wolnych miejsc na {typ_trasy_aktualnej}! Wolne: {wolne},"
                f" Potrzebne: {ilosc_aut}"
            )

    else:
        dopasowane = []
        for c in FLOTA:
            miejsca_zajete = (
                zajete_wyjazd[c["id"]]
                if typ_trasy_aktualnej == "Wyjazd"
                else zajete_powrot[c["id"]]
            )
            wolne = c["pojemnosc"] - miejsca_zajete
            if wolne >= ilosc_aut:
                dopasowane.append({
                    "id": c["id"],
                    "kierowca": c["kierowca"],
                    "pojemnosc": c["pojemnosc"],
                    "wolne_przed": wolne,
                    "zostanie_wolne": wolne - ilosc_aut,
                })

        if dopasowane:
            dopasowane.sort(key=lambda x: x["zostanie_wolne"])
            st.subheader(
                f"Dopasowanie ({typ_trasy_aktualnej}) dla: {ilosc_aut}x"
                f" {marka_model}"
            )
            for item in dopasowane:
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(
                        f"**Kierowca: {item['kierowca']}** (Max:"
                        f" {item['pojemnosc']} aut)"
                    )
                with col2:
                    st.write(
                        f"Wolne na {typ_trasy_aktualnej}:"
                        f" **{item['wolne_przed']}** -> Zostanie:"
                        f" **{item['zostanie_wolne']}**"
                    )
                with col3:
                    if st.button(
                        f"Przypisz do: {item['kierowca']}",
                        key=f"btn_auto_{item['id']}",
                    ):
                        st.session_state.zlecenia.append({
                            "id_zlecenia": datetime.now().timestamp(),
                            "data_wyjazdu": data_wyjazdu_str,
                            "ciężarówka_id": item["id"],
                            "kierowca": item["kierowca"],
                            "typ_trasy": typ_trasy_aktualnej,
                            "marka_model": marka_model,
                            "zrodlo": zrodlo,
                            "skad": skad,
                            "dokad": dokad,
                            "ilosc_aut": ilosc_aut,
                            "cena": cena,
                            "km": km,
                        })
                        zapisz_zlecenia(st.session_state.zlecenia)
                        st.success(
                            "Zlecenie przypisane do kierowcy:"
                            f" {item['kierowca']}!"
                        )
                        st.rerun()
        else:
            st.error(
                "❌ Brak wolnych miejsc u kierowców na trasy typu:"
                f" {typ_trasy_aktualnej}!"
            )

# --- WIDOK ŁADUNKÓW W HARMONOGRAMIE ---
st.subheader("📅 Harmonogram Wyjazdów / Nieprzypisane Zlecenia")

# Pole wyszukiwania
szukaj = st.text_input(
    "🔍 Wyszukaj zlecenie (marka, miasto, źródło, kierowca...)", ""
)

zlecenia_harmonogram = [
    z
    for z in st.session_state.zlecenia
    if z["ciężarówka_id"] is None or z["data_wyjazdu"] > data_wyjazdu_str
]

# Filtrowanie wyszukiwarką
if szukaj:
    szukaj_low = szukaj.lower()
    zlecenia_harmonogram = [
        z
        for z in zlecenia_harmonogram
        if szukaj_low in z["marka_model"].lower()
        or szukaj_low in z["skad"].lower()
        or szukaj_low in z["dokad"].lower()
        or szukaj_low in z["kierowca"].lower()
        or szukaj_low in z.get("zrodlo", "").lower()
    ]

if zlecenia_harmonogram:
    suma_przyszla = sum(z.get("cena", 0) for z in zlecenia_harmonogram)
    st.metric(
        label="Łączny fracht w harmonogramie", value=f"{suma_przyszla} EUR"
    )

    opcje_kierowcow_do_przypisania = [
        f"{c['kierowca']} ({c['pojemnosc']} aut)" for c in FLOTA
    ]

    # Nagłówek Tabeli Harmonogramu
    c_head1, c_head2, c_head3, c_head4, c_head5, c_head6 = st.columns(
        [1.5, 2.5, 2.5, 1.2, 2.5, 0.8]
    )
    with c_head1:
        st.markdown(
            "<span style='font-size:1.1rem;'><b>📅 Data / Kierunek</b></span>",
            unsafe_allow_html=True,
        )
    with c_head2:
        st.markdown(
            "<span style='font-size:1.1rem;'><b>🚘 Pojazd / Źródło</b></span>",
            unsafe_allow_html=True,
        )
    with c_head3:
        st.markdown(
            "<span style='font-size:1.1rem;'><b>📍 Trasa (Skąd ➔ Dokąd)</b></span>",
            unsafe_allow_html=True,
        )
    with c_head4:
        st.markdown(
            "<span style='font-size:1.1rem;'><b>💰 Cena</b></span>",
            unsafe_allow_html=True,
        )
    with c_head5:
        st.markdown(
            "<span style='font-size:1.1rem;'><b>👤 Przypisanie Kierowcy</b></span>",
            unsafe_allow_html=True,
        )
    with c_head6:
        st.markdown(
            "<span style='font-size:1.1rem;'><b>Akcje</b></span>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='margin: 4px 0 12px 0;'>", unsafe_allow_html=True)

    for idx, z in enumerate(
        sorted(zlecenia_harmonogram, key=lambda x: x["data_wyjazdu"])
    ):
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns(
                [1.5, 2.5, 2.5, 1.2, 2.5, 0.8]
            )

            with col1:
                kierunek_badge = (
                    "📤 PL➔ES" if z["typ_trasy"] == "Wyjazd" else "📥 ES➔PL"
                )
                st.markdown(
                    f"<div style='font-size:1.1rem;'><b>{z['data_wyjazdu']}</b><br><small"
                    f" style='font-size:0.95rem;'>{kierunek_badge}</small></div>",
                    unsafe_allow_html=True,
                )

            with col2:
                zrodlo_txt = z.get("zrodlo", "Brak źródła")
                st.markdown(
                    f"<div style='font-size:1.15rem;'><b>{z['ilosc_aut']}x</b>"
                    f" {z['marka_model']}<br><small"
                    " style='background-color:#e0f2fe; color:#0369a1;"
                    " padding:2px 6px; border-radius:4px; font-size:0.85rem;'>🏷️"
                    f" {zrodlo_txt}</small></div>",
                    unsafe_allow_html=True,
                )

            with col3:
                skad_m = z["skad"].split(",")[0]
                dokad_m = z["dokad"].split(",")[0]
                km_info = f" ({z['km']} km)" if z.get("km") else ""
                st.markdown(
                    f"<div style='font-size:1.05rem;'>📍"
                    f" <b>{skad_m}</b><br>➔ <b>{dokad_m}</b><small"
                    f" style='color:gray;'>{km_info}</small></div>",
                    unsafe_allow_html=True,
                )

            with col4:
                st.markdown(
                    f"<span style='color:#2e7d32; font-weight:bold;"
                    f" font-size:1.25rem;'>{z['cena']} €</span>",
                    unsafe_allow_html=True,
                )

            with col5:
                if z["ciężarówka_id"] is None:
                    wybrany_k = st.selectbox(
                        "Wybierz",
                        opcje_kierowcow_do_przypisania,
                        key=f"sel_{z['id_zlecenia']}",
                        label_visibility="collapsed",
                    )
                    if st.button(
                        "👉 Przypisz", key=f"assign_{z['id_zlecenia']}"
                    ):
                        imie_kierowcy = wybrany_k.split(" ")[0]
                        ciężarówka = next(
                            c for c in FLOTA if c["kierowca"] == imie_kierowcy
                        )

                        zlecenia_tydzien = [
                            item
                            for item in st.session_state.zlecenia
                            if item["data_wyjazdu"] == z["data_wyjazdu"]
                            and item["ciężarówka_id"] == ciężarówka["id"]
                            and item["typ_trasy"] == z["typ_trasy"]
                        ]
                        zajete_miejsca = sum(
                            item["ilosc_aut"] for item in zlecenia_tydzien
                        )
                        wolne_miejsca = (
                            ciężarówka["pojemnosc"] - zajete_miejsca
                        )

                        if wolne_miejsca >= z["ilosc_aut"]:
                            for orig_z in st.session_state.zlecenia:
                                if orig_z["id_zlecenia"] == z["id_zlecenia"]:
                                    orig_z["ciężarówka_id"] = ciężarówka["id"]
                                    orig_z["kierowca"] = ciężarówka["kierowca"]
                                    break

                            zapisz_zlecenia(st.session_state.zlecenia)
                            st.success(
                                "Zlecenie przypisano do kierowcy:"
                                f" {ciężarówka['kierowca']}!"
                            )
                            st.rerun()
                        else:
                            st.error(
                                f"Kierowca {ciężarówka['kierowca']} nie ma tylu"
                                f" wolnych miejsc"
                                f" ({wolne_miejsca}/{z['ilosc_aut']})!"
                            )
                else:
                    st.markdown(
                        f"<div style='font-size:1.1rem;'>🚚"
                        f" <b>{z['kierowca']}</b></div>",
                        unsafe_allow_html=True,
                    )

            with col6:
                if st.button(
                    "🗑️",
                    key=f"del_list_{z['id_zlecenia']}",
                    help="Usuń zlecenie",
                ):
                    usun_zlecenie(z["id_zlecenia"])

            st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
else:
    st.info("Brak zleceń w harmonogramie pasujących do wybranych kryteriów.")
