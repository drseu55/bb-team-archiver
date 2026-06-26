import sys

if len(sys.argv) >= 2 and sys.argv[1] == "ui":
    from bb_archive.webui import main as ui_main

    ui_main(sys.argv[2:])
else:
    from bb_archive.cli import main

    main()
