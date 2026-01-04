# Dossier des Certificats de Signature

## ⚠️ IMPORTANT - Sécurité

Ce dossier contient les certificats de signature électronique (`.p12`) qui sont **EXCLUS** du repository Git pour des raisons de sécurité.

## 📁 Structure Requise

Créez les sous-dossiers suivants et placez-y les certificats :

```
signature/
├── nanou/
│   └── [votre_certificat].p12
├── ronald/
│   └── [votre_certificat].p12
├── Yassine/
│   └── AL_KHAITI_MOHAMMED_YASSINE___Y8886816K.p12
└── zakaria/
    └── [votre_certificat].p12
```

## 🔐 Configuration

Après avoir placé les certificats, mettez à jour les chemins et mots de passe dans :

- `app.py` (lignes 66-67, 89, 137-138)
- Voir la documentation principale pour plus de détails

## ⚠️ Ne JAMAIS :

- ❌ Commiter les fichiers `.p12` dans Git
- ❌ Partager les certificats par email
- ❌ Stocker les mots de passe en clair dans le code (utilisez des variables d'environnement)

## 📝 Obtenir un Certificat

Les certificats `.p12` sont généralement fournis par :
- Autorités de certification (CA)
- Votre organisation
- Services de signature électronique

Contactez votre administrateur système pour obtenir vos certificats.



