# 🔐 Dossier des Credentials Google Drive

## ⚠️ IMPORTANT - Sécurité

Ce dossier contient les credentials OAuth Google Drive qui sont **EXCLUS** du repository Git pour des raisons de sécurité.

## 📁 Fichiers Requis (non inclus dans Git)

### 1. `credentials.json`
Téléchargez ce fichier depuis Google Cloud Console :
1. Allez sur [Google Cloud Console](https://console.cloud.google.com)
2. Créez ou sélectionnez votre projet
3. Activez l'API Google Drive
4. Créez des credentials OAuth 2.0 (Application de bureau)
5. Téléchargez le fichier JSON
6. Renommez-le en `credentials.json` et placez-le dans ce dossier

### 2. `token.json`
Ce fichier sera généré automatiquement lors de la première authentification.
- Il contient votre access token et refresh token
- Il se crée après l'autorisation OAuth

## 🔧 Configuration

1. Copiez `credentials.json.example` vers `credentials.json`
2. Remplacez les valeurs par vos vraies credentials Google
3. Lancez l'application - elle ouvrira le navigateur pour l'autorisation
4. Le fichier `token.json` sera créé automatiquement

## 🛡️ Sécurité

### ❌ Ne JAMAIS :
- Commiter `credentials.json` ou `token.json` dans Git
- Partager ces fichiers publiquement
- Les envoyer par email non chiffré

### ✅ Ces fichiers sont protégés par :
- `.gitignore` (ligne 44-45)
- GitHub Secret Scanning (détection automatique)

## 📚 Documentation

- [Guide OAuth Google](https://developers.google.com/identity/protocols/oauth2)
- [API Google Drive](https://developers.google.com/drive/api/v3/about-sdk)


