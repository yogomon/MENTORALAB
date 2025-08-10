
CSS_STRING = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

/* === ESTILOS GENERALES === */
html, body, [class*="st-"], [class*="css-"] {
    font-family: 'Poppins', sans-serif !important;
}
h1 { font-family: 'Poppins', sans-serif !important; font-size: 2.8rem !important; font-weight: 400 !important; }
h2 { font-family: 'Poppins', sans-serif !important; font-size: 1.8rem !important; font-weight: 400 !important; }
h3 { font-family: 'Poppins', sans-serif !important; font-size: 1.2rem !important; font-weight: 400 !important; }
                

/* Fondo general (simple, blanco por defecto) */
body, div#root {
    background-color: #ffffff !important; /* Blanco base */
}

/* === ESTILO CONTENEDOR REUTILIZABLE === */
.app-container,
div[data-testid="stMainBlockContainer"] {
    background-color: #ffffff !important;   /* Fondo Blanco */
    border-radius: 10px !important;       /* Bordes Redondeados */
    padding: 2rem 3rem !important;        /* Relleno Interior */
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08) !important; /* Sombra Suave */
    margin-top: 2rem !important;          /* Margen Superior */
    margin-bottom: 5rem !important;       /* Margen Inferior */
    margin-left: auto !important;         /* Centrado horizontal */
    margin-right: auto !important;        /* Centrado horizontal */
}

/* === ESTILOS BOTONES (Alineación Izquierda Global) === */
div[data-testid="stButton"] > button > div {
    display: flex !important;
    justify-content: flex-start !important; /* Izquierda */
    align-items: center !important;
    width: 100%;
}
div[data-testid="stButton"] > button > div p {
    text-align: left !important;        /* Izquierda */
    margin: 0 !important;
    padding: 0 !important;
    width: auto !important;             /* Ancho auto para texto */
    font-size: inherit !important;      /* Heredar tamaño base (1rem) */
    font-weight: inherit !important;    /* Heredar peso base (400) */
}

/* === ESTILOS Métricas Resumen === */
.metric-container { text-align: center; padding-bottom: 10px; }
.metric-label { font-size: 0.9em !important; color: grey; margin-bottom: 8px !important; font-weight: 400; line-height: 1.2; }
.metric-perc { font-size: 1.6em !important; font-weight: 400; line-height: 1.0; color: #262730; letter-spacing: -1.5px; margin-bottom: 8px !important; display: block; }
.metric-count { font-size: 0.8em !important; color: grey; line-height: 1.2; }

/* === ESTILO DIÁLOGOS === */
div[data-testid="stDialog"] div[role="dialog"] {
    width: 70vw !important;
    max-width: 850px !important;
    min-width: 300px !important;
}
@media (max-width: 600px) {
    div[data-testid="stDialog"] div[role="dialog"] {
        width: 92vw !important;
    }
}

/* === ESTILO BOTÓN LOGOUT === */
div.st-key-logout_button_global button {
    background-color: transparent !important;
    color: #6c757d !important;
    border: none !important;
    padding: 0 !important;
    font-size: inherit !important;
    font-weight: normal !important;
    text-decoration: underline !important;
    box-shadow: none !important;
    display: inline !important;
    line-height: 1 !important;
}
div.st-key-logout_button_global button:hover {
    color: #5a6268 !important;
    text-decoration: underline !important;
    background-color: transparent !important;
}
div.st-key-logout_button_global button:active {
    color: #495057 !important;
    background-color: transparent !important;
}
div.st-key-logout_button_global button p {
    color: inherit !important;
    margin-bottom: 0 !important;
    padding: 0 !important;
}

input, textarea, select, .stTextInput, .stSelectbox {
    font-family: 'Poppins', sans-serif !important;
}

input[type="text"], input[type="password"] {
    font-size: 14px !important; /* Aumentamos el tamaño para que sea muy obvio */
}


</style>
"""
# --- FIN CSS Personalizado ---