python -m PyInstaller --noconfirm --clean --windowed --onedir --name CSCP-MIDI `
  --add-data "korg_sonar_reaper.json;." `
  CSCP-MIDI.py