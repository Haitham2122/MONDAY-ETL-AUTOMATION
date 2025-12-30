# 🔐 Dossier d'Authentification Google Drive

## 📁 Fichiers Requis

Ce dossier doit contenir :

### 1. `credentials.json` ⚠️ OBLIGATOIRE
Fichier de credentials OAuth 2.0 de Google Cloud Console.

**Comment l'obtenir :**

1. **Allez sur Google Cloud Console**
   ```
   https://console.cloud.google.com
   ```

2. **Créer/Sélectionner un Projet**
   - Cliquez sur le sélecteur de projet
   - Créez un nouveau projet OU sélectionnez un existant

3. **Activer l'API Google Drive**
   - Menu : "APIs & Services" → "Library"
   - Recherchez "Google Drive API"
   - Cliquez sur "Enable"

4. **Créer des Credentials**
   - Menu : "APIs & Services" → "Credentials"
   - Cliquez sur "+ CREATE CREDENTIALS"
   - Sélectionnez "OAuth client ID"
   - Type d'application : **"Desktop app"**
   - Donnez-lui un nom (ex: "Monday ETL Automation")
   - Cliquez sur "Create"

5. **Télécharger le fichier JSON**
   - Cliquez sur l'icône de téléchargement (⬇️)
   - Le fichier sera téléchargé (généralement nommé `client_secret_....json`)

6. **Renommer et Placer**
   - Renommez le fichier en `credentials.json`
   - Placez-le dans ce dossier (`auth/credentials.json`)

---

### 2. `token.json` ✅ GÉNÉRÉ AUTOMATIQUEMENT
Ce fichier est créé automatiquement lors de la première authentification.

**Vous n'avez PAS besoin de le créer manuellement.**

Lors de la première exécution :
- Une fenêtre de navigateur s'ouvrira
- Connectez-vous avec votre compte Google
- Autorisez l'accès à Google Drive
- Le fichier `token.json` sera créé automatiquement

---

## 🔒 Sécurité

### ⚠️ IMPORTANT - Ces fichiers sont SECRETS !

- ❌ **NE PAS** les commiter dans Git
- ❌ **NE PAS** les partager par email
- ❌ **NE PAS** les publier en ligne

Ces fichiers sont automatiquement exclus par `.gitignore`.

---

## 🧪 Tester la Connexion

Après avoir placé `credentials.json` :

```bash
# Activer l'environnement virtuel
.venv\Scripts\activate

# Lancer le test
python test_simple_drive.py
```

---

## 🔄 Problèmes d'Authentification

### Si vous voyez "Invalid grant" ou "Token expired"

1. **Supprimer le token :**
   ```bash
   del auth\token.json  # Windows
   rm auth/token.json   # Linux/Mac
   ```

2. **Relancer l'authentification :**
   ```bash
   python test_simple_drive.py
   ```

3. **Une nouvelle fenêtre de navigateur s'ouvrira** pour ré-authentifier

---

## 📋 Structure Finale

```
auth/
├── credentials.json     ← Vous devez le télécharger
├── token.json           ← Généré automatiquement
└── README.md            ← Ce fichier
```

---

## ✅ Checklist

- [ ] Projet créé dans Google Cloud Console
- [ ] API Google Drive activée
- [ ] Credentials OAuth 2.0 créés (type: Desktop app)
- [ ] Fichier téléchargé et renommé en `credentials.json`
- [ ] Fichier placé dans `auth/credentials.json`
- [ ] Test de connexion réussi (`python test_simple_drive.py`)
- [ ] Fichier `token.json` généré automatiquement

---

## 🔗 Liens Utiles

- [Google Cloud Console](https://console.cloud.google.com)
- [Guide OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [Documentation Drive API](https://developers.google.com/drive/api/v3/about-sdk)

