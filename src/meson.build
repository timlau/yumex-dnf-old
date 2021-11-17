python = import('python')

message('Looking for dependencies')
py_installation = python.find_installation('python3')
if not py_installation.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif

python_dir = join_paths(get_option('prefix'), py_installation.get_install_dir())

conf = configuration_data()
conf.set('DATA_DIR', DATA_DIR)
conf.set('PYTHON_DIR', python_dir)
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('localedir')))


install_subdir(
  'yumex',
  install_dir: python_dir
)

message('Preparing bin files')
configure_file(
  input: 'main.py',
  output: 'yumex-dnf',
  configuration: conf,
  install_dir: BIN_DIR
)
configure_file(
  input: 'update.py',
  output: 'yumex-dnf-updatechecker',
  configuration: conf,
  install_dir: BIN_DIR
)
