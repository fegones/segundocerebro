"""Conexión opcional de MCP y Skill a herramientas de agentes.

Sólo realiza cambios con consentimiento. Nunca guarda credenciales de Google en clientes MCP.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path
from .errors import ConfigurationError
from .store import ProfileStore

SERVER = "notebook-conexion"


def skill_contents() -> str:
    return resources.files("notebook_conexion").joinpath("skill/SKILL.md").read_text(encoding="utf-8")


def install_skill_for(agent: str) -> str:
    if agent == "claude":
        target = Path.home() / ".claude" / "skills" / SERVER / "SKILL.md"
    elif agent == "codex":
        target = Path.home() / ".agents" / "skills" / SERVER / "SKILL.md"
    else:
        raise ConfigurationError("Agente desconocido.")
    content = skill_contents()
    if target.is_symlink() or target.parent.is_symlink():
        raise ConfigurationError("Ruta de skill con enlace simbólico no autorizada.")
    if target.exists():
        if target.read_text(encoding="utf-8") == content:
            return "Skill existente, idéntica."
        raise ConfigurationError("Ya existe una skill distinta. No se sobrescribió: " + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return "Skill instalada: " + str(target)


def commands(agent: str, *, profile: str = "personal", allow_writes: bool = False, allow_gemini: bool = False) -> tuple[list[str], list[str]]:
    from .validation import profile_name
    profile_name(profile)
    exe = shutil.which(agent)
    if not exe:
        raise ConfigurationError(f"No encontré '{agent}' en PATH; instale o abra ese agente antes.")
    server_cmd = [sys.executable, "-m", "notebook_conexion.mcp_server", "--profile", profile]
    if allow_writes:
        server_cmd.append("--allow-writes")
    if allow_gemini:
        server_cmd.append("--allow-gemini")
    if agent == "claude":
        return ([exe, "mcp", "get", SERVER],
                [exe, "mcp", "add", "--scope", "user", "--transport", "stdio", SERVER, "--", *server_cmd])
    if agent == "codex":
        return ([exe, "mcp", "get", SERVER],
                [exe, "mcp", "add", SERVER, "--", *server_cmd])
    raise ConfigurationError("Agente desconocido.")


def _call(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConfigurationError("No fue posible ejecutar la configuración del agente.") from exc


def configure(agent: str, *, profile: str = "personal", allow_writes: bool = False,
              allow_gemini: bool = False, replace: bool = False) -> list[str]:
    stored = ProfileStore().load(profile)
    if (allow_writes or allow_gemini) and not stored.allow_write:
        raise ConfigurationError("Debe habilitar primero los envíos/cambios en la política local del perfil.")
    check, add = commands(agent, profile=profile, allow_writes=allow_writes, allow_gemini=allow_gemini)
    result = _call(check)
    if result.returncode == 0:
        if not replace:
            return [f"MCP existente en {agent}; sin cambios. Use --replace con consentimiento para reemplazar.", install_skill_for(agent)]
        removal = _call([check[0], "mcp", "remove", SERVER])
        if removal.returncode != 0:
            raise ConfigurationError("No pude retirar la configuración existente; no se agregó nada.")
    added = _call(add)
    if added.returncode != 0:
        raise ConfigurationError(f"No se pudo registrar MCP en {agent}. Revise la versión de su CLI.")
    return [f"MCP conectado en {agent} al Python de esta instalación.", install_skill_for(agent)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Activar Notebook Conexión para Claude Code/Codex")
    parser.add_argument("--profile", default="personal")
    parser.add_argument("--agent", choices=["claude", "codex"])
    parser.add_argument("--allow-writes", action="store_true")
    parser.add_argument("--allow-gemini", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--interactive-permissions", action="store_true")
    parsed = parser.parse_args(argv)
    agent = parsed.agent
    if not agent:
        print("\n¿A qué agente desea conectar Notebook Conexión?\n  1. Claude Code\n  2. Codex\n  3. Ambos")
        option = input("Opción [1]: ").strip() or "1"
        agents = {"1":["claude"], "2":["codex"], "3":["claude", "codex"]}.get(option)
        if not agents:
            print("Selección inválida.")
            return 2
    else:
        agents = [agent]
    if parsed.interactive_permissions:
        print("\nPermisos de herramientas:\n  1. Solo consultar (recomendado)\n  2. Consultar y cambiar cuadernos/fuentes\n  3. Consultar y generar textos con Gemini API\n  4. Todas las anteriores")
        mode = input("Permiso [1]: ").strip() or "1"
        if mode not in {"1", "2", "3", "4"}:
            print("Permiso inválido.")
            return 2
        parsed.allow_writes = mode in {"2", "4"}
        parsed.allow_gemini = mode in {"3", "4"}
        print("Si un servidor ya está configurado, se propondrá reemplazarlo.")
        parsed.replace = input("¿Autoriza reemplazar una configuración existente del mismo nombre? [s/N]: ").lower() in {"s", "si", "sí"}
    print("\nConfiguración: " + ("MODIFICACIONES AUTORIZADAS" if parsed.allow_writes else "SOLO CONSULTAS"))
    print("Gemini API por agente: " + ("SÍ" if parsed.allow_gemini else "NO"))
    if input("¿Autoriza modificar la configuración de los agentes elegidos? [s/N]: ").lower() not in {"s","si","sí"}:
        print("Operación cancelada.")
        return 1
    for target in agents:
        try:
            for message in configure(target, profile=parsed.profile, allow_writes=parsed.allow_writes,
                                     allow_gemini=parsed.allow_gemini, replace=parsed.replace):
                print(message)
        except ConfigurationError as exc:
            print(f"{target}: {exc}")
    print("\nReinicie el agente y diga: 'Usa Notebook Conexión y enumera mis cuadernos'.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
