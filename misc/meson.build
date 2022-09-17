sassc = find_program('pysassc')



THEME_DIR=join_paths(DATA_DIR, 'themes')
DESKTOP_DIR = join_paths(get_option('prefix'), get_option('datadir'), 'applications')
METAINFO_DIR = join_paths(get_option('prefix'), get_option('datadir'), 'metainfo')


themes = []

sassc_opts = [ '-t', 'expanded' ]


scss_deps = files([
    'scss/_base.scss',
    'scss/_colors.scss',
    'scss/_functions.scss',
    'scss/_palette.scss',
    'scss/_system_base.scss'
])

scss_files = [
    'Dracula',
    'One-Dark',
    'System-Dark',
    'System-Light'
]


foreach scss: scss_files
    themes += custom_target('@0@.theme'.format(scss),
        input: 'scss/@0@.scss'.format(scss),
        output: '@0@.theme'.format(scss),
        command: [sassc, sassc_opts, '@INPUT@', '@OUTPUT@'],
        depend_files: scss_deps, 
        install : true,
        install_dir : THEME_DIR
    )
endforeach

i18n = import('i18n')
desktop_file = i18n.merge_file(
  input: 'yumex-dnf.desktop.in',
  output: 'yumex-dnf.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: DESKTOP_DIR
)

desktop_file_local = i18n.merge_file(
  input: 'yumex-dnf-local.desktop.in',
  output: 'yumex-dnf-local.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: DESKTOP_DIR
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
  test('Validate desktop file', desktop_utils,
    args: [desktop_file_local]
  )
endif

install_data(
  'yumex-dnf-updater.desktop',
  install_dir: DATA_DIR
)

appstream_file = i18n.merge_file(
  input: 'yumex-dnf.appdata.xml.in',
  output: 'yumex-dnf.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: METAINFO_DIR
)

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate', '--nonet', appstream_file]
  )
endif