"""Interfaz de usuario local. Ni claves ni sesiones se muestran en pantalla."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from .errors import BridgeError, ConfigurationError, SecurityError
from .store import Profile, ProfileStore


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="notebook-conexion", description="Gemini Notebook seguro y Segundo Cerebro")
    p.add_argument("--version", action="version", version="Notebook Conexión 1.3.0")
    s = p.add_subparsers(dest="command", required=True)

    def command(name: str, help_text: str):
        sp = s.add_parser(name, help=help_text)
        sp.add_argument("--profile", default="personal", help="Perfil local, no cuenta Google")
        return sp

    init = command("init", "Crear perfil nuevo, sin migraciones heredadas")
    init.add_argument("--project-id", required=True)
    init.add_argument("--client-secrets", required=True, type=Path)

    command("profiles", "Mostrar identificadores de perfiles locales")
    command("gui", "Abrir asistente gráfico para cuentas y agentes")
    command("agents", "Iniciar asistente de conexión MCP de los agentes")
    find = command("search", "Buscar cuadernos por título")
    find.add_argument("--text", required=True)
    export = command("export", "Exportar catálogo local a CSV, JSON, Markdown o Word")
    export.add_argument("--kind", choices=["notebooks", "sources"], default="notebooks")
    export.add_argument("--notebook", default="")
    export.add_argument("--filename", default="catalogo_notebooks")
    export.add_argument("--format", choices=["csv", "json", "md", "txt", "docx"], default="csv")
    generated = command("generate-file", "Crear archivo local mediante Gemini API (NO chat Notebook)")
    generated.add_argument("--prompt", required=True)
    generated.add_argument("--filename", required=True)
    generated.add_argument("--format", choices=["md", "txt", "docx"], default="docx")
    generated.add_argument("--model", default="gemini-3.8-flash")
    auth = command("login", "Vincular propia cuenta Google por OAuth en navegador")
    auth.add_argument("--write", action="store_true", help="Solicitar scope de escritura")
    command("logout", "Olvidar la credencial OAuth del perfil en este equipo")
    policy = command("policy", "Habilitar/deshabilitar envíos y escrituras")
    policy.add_argument("--writes", choices=["on", "off"], required=True)
    policy.add_argument("--ack", default="")
    command("doctor", "Diagnóstico sin exponer claves")
    command("list", "Listar cuadernos")
    show = command("show", "Consultar un cuaderno")
    show.add_argument("--notebook", required=True)
    create = command("create", "Crear cuaderno (requiere escritura)")
    create.add_argument("--title", required=True)
    rename = command("rename", "Cambiar título de cuaderno")
    rename.add_argument("--notebook", required=True)
    rename.add_argument("--title", required=True)
    sources = command("sources", "Listar fuentes")
    sources.add_argument("--notebook", required=True)
    source = command("source", "Consultar metadatos de fuente")
    source.add_argument("--name", required=True)
    url = command("add-url", "Añadir URL HTTPS pública como fuente")
    url.add_argument("--notebook", required=True)
    url.add_argument("--title", required=True)
    url.add_argument("--url", required=True)
    txt = command("add-text", "Añadir fuente desde archivo local de texto")
    txt.add_argument("--notebook", required=True)
    txt.add_argument("--title", required=True)
    txt.add_argument("--file", required=True, type=Path)
    txt.add_argument("--markdown", action="store_true")
    command("scope-show", "Mostrar los cuadernos autorizados del Segundo Cerebro")
    setscope = command("scope-set", "Definir selección persistente, manual y explícita")
    setscope.add_argument("--binding", action="append", required=True,
                          help="Perfil|notebooks/UUID (se repite para múltiples cuadernos)")
    setscope.add_argument("--ack", required=True, help="Confirmación literal RESTRINGIR-CUADERNOS")
    clearscope = command("scope-clear", "Desactivar alcance del Segundo Cerebro")
    clearscope.add_argument("--ack", required=True, help="Confirmación DESACTIVAR-ALCANCE")
    syncbrain = command("brain-sync", "Sincronizar cuadernos seleccionados y opcionalmente texto")
    syncbrain.add_argument("--include-text", action="store_true", help="Intenta recuperar textContent cuando Google lo expone")
    importbrain = command("brain-import", "Importar manualmente un documento a un cuaderno autorizado")
    importbrain.add_argument("--notebook", required=True)
    importbrain.add_argument("--file", required=True, type=Path)
    importbrain.add_argument("--title", default="")
    importbrain.add_argument("--source-id", default="", help="Usar el mismo ID para registrar una nueva versión")
    importbrain.add_argument("--kind", choices=["source", "chat_export", "note_export", "artifact_export"], default="source")
    command("brain-status", "Mostrar alcance y estado local de indexación")
    command("brain-documents", "Documentos indexados del alcance activo")
    auditbrain = command("brain-audit", "Auditar fuentes o cuadernos en múltiples cuentas")
    auditbrain.add_argument("--kind", choices=["sources", "notebooks"], default="sources")
    searchbrain = command("brain-search", "Buscar solo en la evidencia local autorizada")
    searchbrain.add_argument("--question", required=True)
    answerbrain = command("brain-answer", "Responder con evidencia, sin datos externos")
    answerbrain.add_argument("--question", required=True)
    answerbrain.add_argument("--mode", choices=["extractive", "gemini"], default="extractive")
    answerbrain.add_argument("--model", default="gemini-3.8-flash")
    cross = command("brain-compare", "Comparar fuentes de cuentas o cuadernos diferentes")
    cross.add_argument("--profile-a", required=True)
    cross.add_argument("--notebook-a", required=True)
    cross.add_argument("--source-a", required=True)
    cross.add_argument("--profile-b", required=True)
    cross.add_argument("--notebook-b", required=True)
    cross.add_argument("--source-b", required=True)
    diffbrain = command("brain-diff", "Comparar dos versiones de una fuente del alcance seleccionado")
    diffbrain.add_argument("--notebook", required=True)
    diffbrain.add_argument("--source-id", required=True)
    diffbrain.add_argument("--old", required=True, type=int)
    diffbrain.add_argument("--new", required=True, type=int)
    command("set-gemini-key", "Guardar clave propia de Gemini en Keychain/Credential Manager")
    command("clear-gemini-key", "Borrar clave Gemini local")
    gemini = command("gemini", "Consultar Gemini API (no es chat Notebook)")
    gemini.add_argument("--prompt", help="Texto a enviar; usar --file para evitar historiales shell")
    gemini.add_argument("--file", type=Path, help="Leer prompt de archivo")
    gemini.add_argument("--model", default="gemini-3.8-flash")
    return p


def _read_user_text(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise SecurityError("Solo se admiten archivos regulares que no sean enlaces simbólicos.")
    if path.stat().st_size > 1_000_000:
        raise SecurityError("Archivo mayor que 1 MB.")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigurationError("No se pudo leer texto UTF-8.") from exc


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def execute(args: argparse.Namespace, store: ProfileStore | None = None) -> None:
    from . import secrets

    store = store or ProfileStore()
    command = args.command
    if command == "profiles":
        _print({"profiles": store.list_profiles()})
        return
    if command in {"scope-set", "scope-clear", "scope-show"}:
        from .brain_scope import ScopeStore, Binding
        scopes = ScopeStore(profiles=store)
        if command == "scope-show":
            _print({"bindings": [item.key for item in scopes.load()]})
        elif command == "scope-clear":
            if args.ack != "DESACTIVAR-ALCANCE":
                raise SecurityError("Debe confirmar DESACTIVAR-ALCANCE")
            scopes.clear()
            _print({"estado": "sin_alcance", "advertencia": "Vuelven a estar disponibles las herramientas administrativas clásicas MCP."})
        else:
            if args.ack != "RESTRINGIR-CUADERNOS":
                raise SecurityError("Debe confirmar RESTRINGIR-CUADERNOS")
            items = []
            for entry in args.binding:
                if entry.count("|") != 1:
                    raise SecurityError("Use perfil|notebooks/UUID sin otros separadores.")
                items.append(Binding(*entry.split("|")))
            _print({"scope": [x.key for x in scopes.set(items)]})
        return
    if command.startswith("brain-"):
        from .second_brain import SecondBrain
        from .brain_scope import Binding, ScopeStore
        from .brain_store import BrainStore
        brain = SecondBrain(scope=ScopeStore(profiles=store), store=BrainStore(), profiles=store)
        if command == "brain-status":
            _print(brain.status())
        elif command == "brain-sync":
            _print(brain.sync(include_text=args.include_text))
        elif command == "brain-documents":
            _print(brain.documents())
        elif command == "brain-import":
            _print(brain.import_local(Binding(args.profile, args.notebook), args.file, title=args.title,
                                     kind=args.kind, source_id=args.source_id))
        elif command == "brain-audit":
            _print(brain.audit_sources() if args.kind == "sources" else brain.audit_notebooks())
        elif command == "brain-search":
            _print(brain.evidence(args.question))
        elif command == "brain-answer":
            _print(brain.answer(args.question, mode=args.mode,
                                                           allow_gemini=args.mode == "gemini", model=args.model))
        elif command == "brain-diff":
            _print(brain.compare(Binding(args.profile, args.notebook), args.source_id, args.old, args.new))
        elif command == "brain-compare":
            _print(brain.compare_documents(Binding(args.profile_a, args.notebook_a), args.source_a,
                                           Binding(args.profile_b, args.notebook_b), args.source_b))
        return
    if command == "gui":
        from .desktop import main as gui_main
        gui_main()
        return
    if command == "agents":
        from .agent_install import main as agents_main
        agents_main(["--profile", args.profile, "--interactive-permissions"])
        return
    if command == "init":
        if not args.client_secrets.is_file() or args.client_secrets.is_symlink():
            raise ConfigurationError("Archivo OAuth no encontrado o es un enlace simbólico.")
        if store.path(args.profile).exists():
            raise ConfigurationError("El perfil existe; no se sobrescribe silenciosamente.")
        profile = Profile(args.profile, args.project_id, str(args.client_secrets.resolve()))
        # Realiza validación documental, sin importar secretos a este programa.
        from .oauth import _client_secrets

        _client_secrets(profile)
        store.save(profile)
        _print({"profile": profile.name, "status": "created", "allow_write": False})
        return
    profile = store.load(args.profile)
    if command == "doctor":
        from .oauth import _client_secrets

        from . import __version__
        from .secrets import _backend

        _client_secrets(profile)
        _backend()
        _print({"version": __version__, "profile": profile.name, "oauth_config": "valid", "keyring": "available", "writes": profile.allow_write})
        return
    if command == "policy":
        store.enable_write(profile.name, args.writes == "on", args.ack)
        _print({"profile": profile.name, "writes": args.writes})
        return
    if command == "login":
        from .oauth import login

        login(profile, write=args.write)
        _print({"profile": profile.name, "oauth": "connected", "scope": "write" if args.write else "read"})
        return
    if command == "logout":
        secrets.delete_secret(profile.name, "google-oauth")
        _print({"profile": profile.name, "oauth": "removed_locally"})
        return
    if command == "set-gemini-key":
        key = getpass.getpass("Clave de Google AI Studio (entrada oculta): ").strip()
        secrets.set_secret(profile.name, "gemini-api-key", key)
        _print({"gemini_key": "stored_locally"})
        return
    if command == "clear-gemini-key":
        secrets.delete_secret(profile.name, "gemini-api-key")
        _print({"gemini_key": "removed_locally"})
        return
    if command == "gemini":
        from .gemini import GeminiClient

        if bool(args.prompt) == bool(args.file):
            raise SecurityError("Proporcione --prompt o --file, exactamente uno.")
        prompt = args.prompt if args.prompt is not None else _read_user_text(args.file)
        print(GeminiClient(profile).generate(prompt, model=args.model))
        return
    if command == "search":
        from .catalog import find_notebooks
        from .notebook import NotebookClient
        _print(find_notebooks(NotebookClient(profile), args.text))
        return
    if command == "export":
        from .operations import Operations
        _print(Operations(profile).export_catalog(args.kind, args.filename, args.format, args.notebook))
        return
    if command == "generate-file":
        from .operations import Operations
        _print(Operations(profile, agent_gemini=True).generate_file(args.prompt, args.filename, args.format, args.model))
        return
    from .notebook import NotebookClient
    client = NotebookClient(profile)
    if command == "list":
        _print(client.notebooks())
    elif command == "show":
        _print(client.notebook(args.notebook))
    elif command == "create":
        _print(client.create(args.title))
    elif command == "rename":
        _print(client.rename(args.notebook, args.title))
    elif command == "sources":
        _print(client.sources(args.notebook))
    elif command == "source":
        _print(client.source(args.name))
    elif command == "add-url":
        _print(client.add_url(args.notebook, args.title, args.url))
    elif command == "add-text":
        _print(client.add_text(args.notebook, args.title, _read_user_text(args.file), markdown=args.markdown))
    else:
        raise ConfigurationError("Comando no implementado.")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        execute(args)
    except BridgeError as exc:
        # Excepción controlada: nunca se imprimen el stacktrace ni el token.
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
