"""
Script simple pour tester rapidement la connexion Google Drive
"""

import os
import sys

# Vérifier que credentials.json existe
if not os.path.exists("auth/credentials.json"):
    print("❌ ERREUR: Le fichier auth/credentials.json n'existe pas!")
    print("\n📝 Instructions:")
    print("1. Allez sur https://console.cloud.google.com")
    print("2. Créez/sélectionnez un projet")
    print("3. Activez l'API Google Drive")
    print("4. Créez des credentials OAuth 2.0 (Application de bureau)")
    print("5. Téléchargez le fichier JSON et placez-le dans auth/credentials.json")
    sys.exit(1)

print("✅ credentials.json trouvé!")
print("🚀 Lancement du test complet...\n")

# Importer et lancer le test complet
from test_google_drive import main
main()

