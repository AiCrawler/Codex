# Dashboard KPI da Excel

Applicazione web realizzata con [Streamlit](https://streamlit.io/) che permette di caricare file Excel e generare automaticamente dashboard interattive di KPI.

## Funzionalità principali
- Caricamento di file `.xls` e `.xlsx` con supporto multi-foglio.
- Riconoscimento automatico delle colonne numeriche e testuali.
- Calcolo di KPI riepilogativi e statistiche descrittive.
- Creazione di grafici interattivi per analisi per dimensione.
- Analisi dei trend temporali con possibilità di aggregare per diverse frequenze.

## Requisiti
- Python 3.10+

Installa le dipendenze con:

```bash
pip install -r requirements.txt
```

## Avvio dell'applicazione

```bash
streamlit run app.py
```

Carica un file Excel dalla pagina dell'applicazione per esplorare automaticamente KPI e grafici.
