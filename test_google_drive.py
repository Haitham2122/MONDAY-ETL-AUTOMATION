"""
Script de test pour vérifier la connexion Google Drive
et uploader le certificat .p12 de Ronald
"""

import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Configuration
SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_PATH = "auth/credentials.json"
TOKEN_PATH = "auth/token.json"

def test_credentials_exists():
    """Vérifie si le fichier credentials.json existe"""
    print("=" * 60)
    print("🔍 ÉTAPE 1: Vérification du fichier credentials.json")
    print("=" * 60)
    
    if os.path.exists(CREDENTIALS_PATH):
        print(f"✅ Fichier trouvé: {CREDENTIALS_PATH}")
        
        # Lire et afficher les informations (sans les secrets)
        try:
            with open(CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
                creds_data = json.load(f)
                
            if 'installed' in creds_data:
                client_id = creds_data['installed'].get('client_id', 'N/A')
                project_id = creds_data['installed'].get('project_id', 'N/A')
                print(f"   📋 Project ID: {project_id}")
                print(f"   🔑 Client ID: {client_id[:50]}...")
                return True
            else:
                print("   ⚠️ Format du fichier credentials.json non reconnu")
                return False
        except Exception as e:
            print(f"   ❌ Erreur lors de la lecture: {str(e)}")
            return False
    else:
        print(f"❌ Fichier manquant: {CREDENTIALS_PATH}")
        print("\n📝 Instructions pour obtenir credentials.json:")
        print("   1. Allez sur: https://console.cloud.google.com")
        print("   2. Créez/sélectionnez un projet")
        print("   3. Activez l'API Google Drive")
        print("   4. Créez des credentials OAuth 2.0 (Application de bureau)")
        print("   5. Téléchargez le fichier JSON")
        print("   6. Renommez-le en 'credentials.json'")
        print(f"   7. Placez-le dans: {os.path.abspath(CREDENTIALS_PATH)}")
        return False


def authenticate_google_drive():
    """Authentifie l'utilisateur et retourne le service Google Drive"""
    print("\n" + "=" * 60)
    print("🔐 ÉTAPE 2: Authentification Google Drive")
    print("=" * 60)
    
    creds = None
    
    # Vérifier si token.json existe
    if os.path.exists(TOKEN_PATH):
        print(f"📄 Token existant trouvé: {TOKEN_PATH}")
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            print("✅ Token chargé avec succès")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement du token: {str(e)}")
            creds = None
    
    # Si pas de credentials valides, obtenir de nouveaux
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Rafraîchissement du token expiré...")
            try:
                creds.refresh(Request())
                print("✅ Token rafraîchi avec succès")
            except Exception as e:
                print(f"❌ Erreur lors du rafraîchissement: {str(e)}")
                return None
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"❌ Fichier credentials.json manquant: {CREDENTIALS_PATH}")
                return None
            
            print("🌐 Ouverture du navigateur pour l'authentification...")
            print("   (Une fenêtre de navigateur va s'ouvrir)")
            
            try:
                with open(CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
                    client_config = json.load(f)
                
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                creds = flow.run_local_server(port=0)
                print("✅ Authentification réussie!")
                
                # Sauvegarder le token
                with open(TOKEN_PATH, 'w', encoding='utf-8') as token:
                    token.write(creds.to_json())
                print(f"💾 Token sauvegardé dans: {TOKEN_PATH}")
                
            except Exception as e:
                print(f"❌ Erreur lors de l'authentification: {str(e)}")
                return None
    
    # Créer le service Drive
    try:
        service = build("drive", "v3", credentials=creds)
        print("✅ Service Google Drive créé avec succès")
        return service
    except Exception as e:
        print(f"❌ Erreur lors de la création du service: {str(e)}")
        return None


def test_drive_connection(service):
    """Test la connexion en listant les fichiers"""
    print("\n" + "=" * 60)
    print("🔍 ÉTAPE 3: Test de connexion - Liste des fichiers")
    print("=" * 60)
    
    try:
        # Lister les 10 premiers fichiers
        results = service.files().list(
            pageSize=10,
            fields="files(id, name, mimeType, createdTime)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print("📂 Aucun fichier trouvé dans votre Google Drive")
        else:
            print(f"✅ Connexion réussie! {len(items)} fichiers trouvés:")
            for item in items:
                print(f"   📄 {item['name']} (ID: {item['id']})")
        
        return True
    except Exception as e:
        print(f"❌ Erreur lors du test de connexion: {str(e)}")
        return False


def upload_p12_file(service):
    """Upload le fichier .p12 de Ronald vers Google Drive"""
    print("\n" + "=" * 60)
    print("📤 ÉTAPE 4: Upload du certificat .p12 de Ronald")
    print("=" * 60)
    
    # Chercher le fichier .p12 dans signature/ronald/
    p12_dir = "signature/ronald"
    
    if not os.path.exists(p12_dir):
        print(f"❌ Dossier manquant: {p12_dir}")
        print(f"   📁 Créer le dossier: {os.path.abspath(p12_dir)}")
        return False
    
    # Lister les fichiers .p12
    p12_files = [f for f in os.listdir(p12_dir) if f.endswith('.p12')]
    
    if not p12_files:
        print(f"❌ Aucun fichier .p12 trouvé dans: {p12_dir}")
        print("\n📝 Instructions:")
        print(f"   1. Placez le certificat .p12 de Ronald dans: {os.path.abspath(p12_dir)}")
        print("   2. Relancez ce script")
        return False
    
    print(f"✅ Fichiers .p12 trouvés: {len(p12_files)}")
    
    # Upload chaque fichier
    uploaded_files = []
    for p12_file in p12_files:
        file_path = os.path.join(p12_dir, p12_file)
        file_size = os.path.getsize(file_path)
        
        print(f"\n📤 Upload de: {p12_file} ({file_size} bytes)")
        
        try:
            # Métadonnées du fichier
            file_metadata = {
                'name': f"TEST_{p12_file}",  # Préfixe TEST pour identifier
                'description': 'Test upload - Certificat Ronald'
            }
            
            # Upload
            media = MediaFileUpload(
                file_path,
                mimetype='application/x-pkcs12',
                resumable=True
            )
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, size'
            ).execute()
            
            print(f"✅ Upload réussi!")
            print(f"   📋 Nom: {file.get('name')}")
            print(f"   🆔 ID: {file.get('id')}")
            print(f"   💾 Taille: {file.get('size')} bytes")
            print(f"   🔗 Lien: {file.get('webViewLink')}")
            
            uploaded_files.append(file)
            
        except Exception as e:
            print(f"❌ Erreur lors de l'upload: {str(e)}")
            continue
    
    if uploaded_files:
        print(f"\n🎉 {len(uploaded_files)} fichier(s) uploadé(s) avec succès!")
        return True
    else:
        print("\n❌ Aucun fichier n'a pu être uploadé")
        return False


def create_test_folder(service, folder_name="TEST_RONALD_CERTS"):
    """Crée un dossier de test dans Google Drive"""
    print("\n" + "=" * 60)
    print(f"📁 ÉTAPE 5: Création du dossier de test: {folder_name}")
    print("=" * 60)
    
    try:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'description': 'Dossier de test pour certificats Ronald'
        }
        
        folder = service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        print(f"✅ Dossier créé avec succès!")
        print(f"   📋 Nom: {folder.get('name')}")
        print(f"   🆔 ID: {folder.get('id')}")
        print(f"   🔗 Lien: {folder.get('webViewLink')}")
        
        return folder.get('id')
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du dossier: {str(e)}")
        return None


def main():
    """Fonction principale"""
    print("\n" + "🚀" * 30)
    print("   TEST DE CONNEXION GOOGLE DRIVE + UPLOAD P12 RONALD")
    print("🚀" * 30 + "\n")
    
    # Étape 1: Vérifier credentials.json
    if not test_credentials_exists():
        print("\n❌ ARRÊT: Fichier credentials.json manquant")
        print("   Suivez les instructions ci-dessus pour l'obtenir.")
        return
    
    # Étape 2: Authentification
    service = authenticate_google_drive()
    if not service:
        print("\n❌ ARRÊT: Échec de l'authentification")
        return
    
    # Étape 3: Test de connexion
    if not test_drive_connection(service):
        print("\n❌ ARRÊT: Échec du test de connexion")
        return
    
    # Étape 4: Créer un dossier de test
    folder_id = create_test_folder(service)
    
    # Étape 5: Upload du fichier .p12
    upload_p12_file(service)
    
    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ FINAL")
    print("=" * 60)
    print("✅ Credentials.json: OK")
    print("✅ Authentification: OK")
    print("✅ Connexion Drive: OK")
    if folder_id:
        print(f"✅ Dossier créé: {folder_id}")
    print("\n🎉 Test terminé avec succès!")
    print("\n💡 Prochaines étapes:")
    print("   1. Vérifiez les fichiers uploadés dans votre Google Drive")
    print("   2. Copiez l'ID du dossier racine pour l'utiliser dans app.py")
    print("   3. Supprimez les fichiers de test si nécessaire")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ ERREUR CRITIQUE: {str(e)}")
        import traceback
        traceback.print_exc()

