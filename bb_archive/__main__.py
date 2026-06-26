import sys

if len(sys.argv) >= 2 and sys.argv[1] == "ui":
    from .webui import main as ui_main

    ui_main(sys.argv[2:])
else:
    from .cli import main

    main()
