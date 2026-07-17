import argparse
from dotenv import load_dotenv

load_dotenv()

from pi import config
from pi.chat import start_chat_loop

if __name__ == "__main__":
    cfg = config.load()
    parser = argparse.ArgumentParser(description="Pi — AI coding assistant")
    subparsers = parser.add_subparsers(dest="command")

    # Default chat command (no subcommand)
    parser.add_argument(
        "--provider", "-p",
        default=cfg["provider"],
        help=f"AI provider: gemini or openai (default: {cfg['provider']})",
    )
    parser.add_argument(
        "--session", "-s",
        default="default",
        help="Session name (default: 'default')",
    )

    # telegram subcommand
    tg = subparsers.add_parser("telegram", help="Start Pi as a Telegram bot")
    tg.add_argument(
        "--token", "-t",
        default=cfg.get("telegram_token", ""),
        help="Telegram bot token (or set via: python main.py config set telegram_token <token>)",
    )

    # config subcommand (for setting values from the terminal)
    cfg_cmd = subparsers.add_parser("config", help="Get or set config values")
    cfg_cmd.add_argument("action", nargs="?", choices=["set"], help="Action to perform")
    cfg_cmd.add_argument("key", nargs="?", help="Config key")
    cfg_cmd.add_argument("value", nargs="?", help="Config value")

    args = parser.parse_args()

    if args.command == "telegram":
        token = args.token
        if not token:
            print("Error: no Telegram token.")
            print("Run: python main.py config set telegram_token <token>")
            raise SystemExit(1)
        from pi.telegram_bot import run
        run(token)
    elif args.command == "config":
        if args.action == "set":
            if not args.key or not args.value:
                print("Usage: python main.py config set <key> <value>")
                raise SystemExit(1)
            ok, msg = config.set_value(args.key, args.value)
            print(msg)
            raise SystemExit(0 if ok else 1)
        else:
            from pi.chat import _print_config
            _print_config(cfg)
    else:
        start_chat_loop(provider=args.provider, session_name=args.session)
