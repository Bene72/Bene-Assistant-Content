#!/bin/bash
# Prépare l'environnement de Claude pour les animations 3D BEN&FIT.
# À lancer depuis la racine du dépôt : bash contenu/benfit-3d/setup.sh
set -e
cd /home/claude
mkdir -p work fonts assets/mh scripts
cp "$(dirname "$0")"/scripts/*.py scripts/

# Blender (moteur de rendu) en module Python
python3 -c "import bpy" 2>/dev/null || pip install --break-system-packages -q bpy scipy

# Détection du mouvement : MediaPipe 0.10.14 a besoin de Python 3.11
if [ ! -x mp311/bin/python ]; then
  command -v uv >/dev/null || pip install --break-system-packages -q uv
  uv venv -q -p 3.11 mp311
  uv pip install -q -p mp311/bin/python "mediapipe==0.10.14" opencv-python-headless "numpy<2" scipy
fi

# Corps humain de base (MakeHuman, licence CC0) et police Coda
[ -f assets/mh/base.obj ] || curl -sSL -o assets/mh/base.obj \
  https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/3dobjs/base.obj
for f in Coda-Regular Coda-ExtraBold; do
  [ -f fonts/$f.ttf ] || curl -sSL -o fonts/$f.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/coda/$f.ttf
done
[ -f work/mh.json ] || python3 scripts/parse_mh.py assets/mh/base.obj work/mh.json >/dev/null
echo "Environnement prêt."
