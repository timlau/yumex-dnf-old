project('yumex-dnf',  
          version: '4.4.0',
    meson_version: '>= 0.50.0'
)

APPNAME = meson.project_name()
DATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
BIN_DIR = join_paths(get_option('prefix'), get_option('bindir'))

subdir('src')
subdir('data')
subdir('gfx')
subdir('misc')
subdir('po')
