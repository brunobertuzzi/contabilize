
import webview
import logging
import sys
from scripts.config import Config

def start_gui(app):
    """Inicia a interface gráfica com pywebview."""
    try:
        window = webview.create_window(
            Config.APP_NAME,
            app,
            width=1280,
            height=800,
            resizable=True,
            min_size=(800, 600),
            hidden=False,
            frameless=False,
            easy_drag=True,
            confirm_close=True,
            text_select=True,
            localization={'global.quitConfirmation': 'Você tem certeza que quer sair?'}
        )
        
        webview.start(debug=False)
        
    except Exception as e:
        logging.error(f"Erro ao iniciar a interface gráfica: {e}")
        sys.exit(1)
