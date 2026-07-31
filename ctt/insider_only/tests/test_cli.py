import importlib


def test_package_can_be_imported():
    assert importlib.import_module("the_project") is not None


def test_cli(capsys):
    from the_project.__main__ import main

    main()

    assert capsys.readouterr().out == "the-project\n"
