# 🧪 Scripts de Test Google Drive

## 📋 Fichiers de Test

### 1. `test_google_drive.py` - Test Complet
Script détaillé qui teste :
- ✅ Vérification de `credentials.json`
- ✅ Authentification Google Drive
- ✅ Connexion et liste des fichiers
- ✅ Création d'un dossier de test
- ✅ Upload du certificat `.p12` de Ronald

### 2. `test_simple_drive.py` - Test Rapide
Script simple qui vérifie juste la présence de `credentials.json` et lance le test complet.

---

## 🚀 Comment Utiliser

### Prérequis

1. **Obtenir `credentials.json`** depuis Google Cloud Console :
   
   ```
   https://console.cloud.google.com
   ```
   
   Étapes :
   - Créer/sélectionner un projet
   - Activer l'API Google Drive
   - Créer des credentials OAuth 2.0 (Application de bureau)
   - Télécharger le fichier JSON
   - Renommer en `credentials.json`
   - Placer dans `auth/credentials.json`

2. **Placer le certificat `.p12` de Ronald** :
   
   ```
   signature/ronald/[votre_certificat].p12
   ```

---

## 📝 Instructions Étape par Étape

### Option 1 : Test Simple (Recommandé)

```bash
# Activer l'environnement virtuel
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Lancer le test
python test_simple_drive.py
```

### Option 2 : Test Complet

```bash
# Activer l'environnement virtuel
.venv\Scripts\activate  # Windows

# Lancer le test complet
python test_google_drive.py
```

---

## 📊 Ce que Font les Scripts

### Étape 1 : Vérification de `credentials.json`
- Vérifie que le fichier existe
- Affiche le Project ID et Client ID
- Donne des instructions si manquant

### Étape 2 : Authentification
- Charge le token existant (`auth/token.json`) si disponible
- Sinon, ouvre le navigateur pour l'authentification OAuth
- Sauvegarde le token pour les futures utilisations

### Étape 3 : Test de Connexion
- Liste les 10 premiers fichiers de votre Google Drive
- Confirme que la connexion fonctionne

### Étape 4 : Création de Dossier
- Crée un dossier de test nommé `TEST_RONALD_CERTS`
- Affiche l'ID du dossier créé

### Étape 5 : Upload du Certificat
- Recherche les fichiers `.p12` dans `signature/ronald/`
- Upload chaque fichier trouvé (avec préfixe `TEST_`)
- Affiche les liens vers les fichiers uploadés

---

## ✅ Résultat Attendu

Si tout fonctionne, vous verrez :

```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
   TEST DE CONNEXION GOOGLE DRIVE + UPLOAD P12 RONALD
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

============================================================
🔍 ÉTAPE 1: Vérification du fichier credentials.json
============================================================
✅ Fichier trouvé: auth/credentials.json
   📋 Project ID: votre-projet-id
   🔑 Client ID: 123456789...

============================================================
🔐 ÉTAPE 2: Authentification Google Drive
============================================================
✅ Token chargé avec succès
✅ Service Google Drive créé avec succès

============================================================
🔍 ÉTAPE 3: Test de connexion - Liste des fichiers
============================================================
✅ Connexion réussie! 10 fichiers trouvés:
   📄 Document1.pdf (ID: abc123...)
   📄 Image.jpg (ID: def456...)
   ...

============================================================
📁 ÉTAPE 4: Création du dossier de test: TEST_RONALD_CERTS
============================================================
✅ Dossier créé avec succès!
   📋 Nom: TEST_RONALD_CERTS
   🆔 ID: xyz789...
   🔗 Lien: https://drive.google.com/...

============================================================
📤 ÉTAPE 5: Upload du certificat .p12 de Ronald
============================================================
✅ Fichiers .p12 trouvés: 1

📤 Upload de: ronald_cert.p12 (1234 bytes)
✅ Upload réussi!
   📋 Nom: TEST_ronald_cert.p12
   🆔 ID: aaa111...
   💾 Taille: 1234 bytes
   🔗 Lien: https://drive.google.com/...

🎉 1 fichier(s) uploadé(s) avec succès!

============================================================
📊 RÉSUMÉ FINAL
============================================================
✅ Credentials.json: OK
✅ Authentification: OK
✅ Connexion Drive: OK
✅ Dossier créé: xyz789...

🎉 Test terminé avec succès!

💡 Prochaines étapes:
   1. Vérifiez les fichiers uploadés dans votre Google Drive
   2. Copiez l'ID du dossier racine pour l'utiliser dans app.py
   3. Supprimez les fichiers de test si nécessaire
```

---

## ❌ Problèmes Courants

### Erreur : `credentials.json manquant`
**Solution :** Téléchargez le fichier depuis Google Cloud Console et placez-le dans `auth/credentials.json`

### Erreur : `Aucun fichier .p12 trouvé`
**Solution :** Placez votre certificat `.p12` dans `signature/ronald/`

### Erreur : `API not enabled`
**Solution :** Activez l'API Google Drive dans Google Cloud Console

### Erreur : `Invalid grant`
**Solution :** Supprimez `auth/token.json` et relancez le script pour ré-authentifier

---

## 🔐 Sécurité

⚠️ **NE PAS** commiter dans Git :
- `auth/credentials.json`
- `auth/token.json`
- `signature/*/*.p12`

Ces fichiers sont automatiquement exclus par `.gitignore`.

---

## 🧹 Nettoyage Après Test

Après avoir vérifié que tout fonctionne :

1. **Supprimer les fichiers de test** dans Google Drive :
   - Dossier `TEST_RONALD_CERTS`
   - Fichiers avec préfixe `TEST_`

2. **Garder les fichiers locaux** :
   - `auth/credentials.json` (nécessaire)
   - `auth/token.json` (généré automatiquement)
   - `signature/ronald/*.p12` (nécessaire pour la signature)

---

## 📞 Support

Si vous rencontrez des problèmes :
1. Vérifiez que l'API Google Drive est activée
2. Vérifiez les permissions OAuth (scope: drive)
3. Consultez les logs d'erreur détaillés

---

## 🔗 Liens Utiles

- [Google Cloud Console](https://console.cloud.google.com)
- [Documentation Google Drive API](https://developers.google.com/drive/api/v3/about-sdk)
- [Guide OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)

