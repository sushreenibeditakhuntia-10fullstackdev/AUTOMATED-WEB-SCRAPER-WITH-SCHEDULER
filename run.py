"""
Entry point: python run.py
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"""
╔══════════════════════════════════════════════════════╗
║          Automated Web Scraper with Scheduler        ║
╠══════════════════════════════════════════════════════╣
║  Dashboard  →  http://localhost:{port:<4}                 ║
║  API Base   →  http://localhost:{port:<4}/api             ║
║  Health     →  http://localhost:{port:<4}/api/health      ║
╚══════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=debug)
