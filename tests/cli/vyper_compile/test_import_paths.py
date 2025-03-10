import pytest

from vyper.cli.vyper_compile import (
    compile_files,
    get_interface_file_path,
)

FOO_CODE = """
{}

@public
def foo() -> uint256:
    return 13

@public
def bar(a: address) -> uint256:
    return Bar(a).bar()
"""

BAR_CODE = """
@public
def bar() -> uint256:
    return 13
"""


SAME_FOLDER_IMPORT_STMT = [
    "import Bar as Bar",
    "import contracts.Bar as Bar",
    "from . import Bar",
    "from contracts import Bar",
    "from ..contracts import Bar",
]


@pytest.mark.parametrize('import_stmt', SAME_FOLDER_IMPORT_STMT)
def test_import_same_folder(import_stmt, tmp_path):
    tmp_path.joinpath('contracts').mkdir()

    foo_path = tmp_path.joinpath('contracts/foo.vy')
    with foo_path.open('w') as fp:
        fp.write(FOO_CODE.format(import_stmt))

    with tmp_path.joinpath('contracts/Bar.vy').open('w') as fp:
        fp.write(BAR_CODE)

    assert compile_files([foo_path], ['combined_json'], root_folder=tmp_path)


SUBFOLDER_IMPORT_STMT = [
    "import other.Bar as Bar",
    "import contracts.other.Bar as Bar",
    "from other import Bar",
    "from contracts.other import Bar",
    "from .other import Bar",
    "from ..contracts.other import Bar",
]


@pytest.mark.parametrize('import_stmt', SUBFOLDER_IMPORT_STMT)
def test_import_subfolder(import_stmt, tmp_path):
    tmp_path.joinpath('contracts').mkdir()

    foo_path = tmp_path.joinpath('contracts/foo.vy')
    with foo_path.open('w') as fp:
        fp.write(FOO_CODE.format(import_stmt))

    tmp_path.joinpath('contracts/other').mkdir()
    with tmp_path.joinpath('contracts/other/Bar.vy').open('w') as fp:
        fp.write(BAR_CODE)

    assert compile_files([foo_path], ['combined_json'], root_folder=tmp_path)


OTHER_FOLDER_IMPORT_STMT = [
    "import interfaces.Bar as Bar",
    "from interfaces import Bar",
    "from ..interfaces import Bar",
]


@pytest.mark.parametrize('import_stmt', OTHER_FOLDER_IMPORT_STMT)
def test_import_other_folder(import_stmt, tmp_path):
    tmp_path.joinpath('contracts').mkdir()

    foo_path = tmp_path.joinpath('contracts/foo.vy')
    with foo_path.open('w') as fp:
        fp.write(FOO_CODE.format(import_stmt))

    tmp_path.joinpath('interfaces').mkdir()
    with tmp_path.joinpath('interfaces/Bar.vy').open('w') as fp:
        fp.write(BAR_CODE)

    assert compile_files([foo_path], ['combined_json'], root_folder=tmp_path)


def test_import_parent_folder(tmp_path, assert_compile_failed):
    tmp_path.joinpath('contracts').mkdir()

    foo_path = tmp_path.joinpath('contracts/foo.vy')
    with foo_path.open('w') as fp:
        fp.write(FOO_CODE.format("from .. import Bar"))

    with tmp_path.joinpath('Bar.vy').open('w') as fp:
        fp.write(BAR_CODE)

    assert compile_files([foo_path], ['combined_json'], root_folder=tmp_path)
    # Cannot perform relative import outside of base folder
    with pytest.raises(FileNotFoundError):
        compile_files([foo_path], ['combined_json'], root_folder=tmp_path.joinpath('contracts'))


META_IMPORT_STMT = [
    "import Meta as Meta",
    "import contracts.Meta as Meta",
    "from . import Meta",
    "from contracts import Meta",
]


@pytest.mark.parametrize('import_stmt', META_IMPORT_STMT)
def test_import_self_interface(import_stmt, tmp_path):
    # a contract can access it's derived interface by importing itself
    code = """
{}

@public
def know_thyself(a: address) -> uint256:
    return Meta(a).be_known()

@public
def be_known() -> uint256:
    return 42
    """.format(import_stmt)

    tmp_path.joinpath('contracts').mkdir()

    meta_path = tmp_path.joinpath('contracts/Meta.vy')
    with meta_path.open('w') as fp:
        fp.write(code)

    assert compile_files([meta_path], ['combined_json'], root_folder=tmp_path)


DERIVED_IMPORT_STMT_BAZ = [
    "import Foo as Foo",
    "from . import Foo",
]

DERIVED_IMPORT_STMT_FOO = [
    "import Bar as Bar",
    "from . import Bar",
]


@pytest.mark.parametrize('import_stmt_baz', DERIVED_IMPORT_STMT_BAZ)
@pytest.mark.parametrize('import_stmt_foo', DERIVED_IMPORT_STMT_FOO)
def test_derived_interface_imports(import_stmt_baz, import_stmt_foo, tmp_path):
    # contracts-as-interfaces should be able to contain import statements
    baz_code = """
{}

@public
def foo(a: address) -> uint256:
    return Foo(a).foo()

@public
def bar(_foo: address, _bar: address) -> uint256:
    return Foo(_foo).bar(_bar)
    """.format(import_stmt_baz)

    with tmp_path.joinpath('Foo.vy').open('w') as fp:
        fp.write(FOO_CODE.format(import_stmt_foo))

    with tmp_path.joinpath('Bar.vy').open('w') as fp:
        fp.write(BAR_CODE)

    baz_path = tmp_path.joinpath('Baz.vy')
    with baz_path.open('w') as fp:
        fp.write(baz_code)

    assert compile_files([baz_path], ['combined_json'], root_folder=tmp_path)


def test_local_namespace(tmp_path):
    # interface code namespaces should be isolated
    # all of these contract should be able to compile together
    codes = [
        "import foo as FooBar",
        "import bar as FooBar",
        "import foo as BarFoo",
        "import bar as BarFoo",
    ]

    compile_paths = []
    for i, code in enumerate(codes):
        path = tmp_path.joinpath(f'code{i}.vy')
        with path.open('w') as fp:
            fp.write(code)
        compile_paths.append(path)

    for file_name in ('foo.vy', 'bar.vy'):
        with tmp_path.joinpath(file_name).open('w') as fp:
            fp.write(BAR_CODE)

    assert compile_files(compile_paths, ['combined_json'], root_folder=tmp_path)


def test_get_interface_file_path(tmp_path):
    for file_name in ('foo.vy', 'foo.json', 'bar.vy', 'baz.json', 'potato'):
        with tmp_path.joinpath(file_name).open('w') as fp:
            fp.write("")

    tmp_path.joinpath('interfaces').mkdir()
    for file_name in ('interfaces/foo.json', 'interfaces/bar'):
        with tmp_path.joinpath(file_name).open('w') as fp:
            fp.write("")

    base_paths = [tmp_path, tmp_path.joinpath('interfaces')]
    assert get_interface_file_path(base_paths, 'foo') == tmp_path.joinpath('foo.vy')
    assert get_interface_file_path(base_paths, 'bar') == tmp_path.joinpath('bar.vy')
    assert get_interface_file_path(base_paths, 'baz') == tmp_path.joinpath('baz.json')

    base_paths = [tmp_path.joinpath('interfaces'), tmp_path]
    assert get_interface_file_path(base_paths, 'foo') == tmp_path.joinpath('interfaces/foo.json')
    assert get_interface_file_path(base_paths, 'bar') == tmp_path.joinpath('bar.vy')
    assert get_interface_file_path(base_paths, 'baz') == tmp_path.joinpath('baz.json')

    with pytest.raises(Exception):
        get_interface_file_path(base_paths, 'potato')


def test_compile_outside_root_path(tmp_path):
    foo_path = tmp_path.joinpath('foo.vy')
    with foo_path.open('w') as fp:
        fp.write(FOO_CODE.format('import bar as Bar'))

    bar_path = tmp_path.joinpath('bar.vy')
    with bar_path.open('w') as fp:
        fp.write(BAR_CODE)

    assert compile_files([foo_path, bar_path], ['combined_json'], root_folder=".")
