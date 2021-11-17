ICON_DIR_SVG = join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/scalable/apps/')
ICON_DIR_PNG = join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/48x48/apps/')
DATA_DIR_GFX = join_paths(get_option('prefix'), get_option('datadir'), APPNAME,'gfx')

install_data(
    APPNAME+'.svg',
    install_dir: ICON_DIR_SVG
)
install_data(
    APPNAME+'.png',
    install_dir: ICON_DIR_PNG
)
install_data(
    'progress.gif',
    install_dir: DATA_DIR_GFX
)
