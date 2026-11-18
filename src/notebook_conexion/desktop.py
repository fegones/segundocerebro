"""Panel Tkinter opcional. No contiene vistas web ni tokens integrados."""
from __future__ import annotations
import json
import threading
import webbrowser
from .errors import BridgeError


def main() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
    except ImportError as exc:
        raise RuntimeError("Su Python no incluye Tkinter. Use el asistente de consola.") from exc

    from .catalog import all_notebooks
    from .exports import export_directory
    from .notebook import NotebookClient
    from .oauth import _client_secrets, login
    from .secrets import set_secret
    from .store import Profile, ProfileStore

    store = ProfileStore()
    app = tk.Tk()
    app.title("Notebook Conexión 1.3.0 | Ideas Innovadoras")
    app.geometry("950x730")
    app.minsize(710, 580)

    frame = ttk.Frame(app, padding=17)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Notebook Conexión 1.3.0", font=("Segoe UI", 17, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Su cuenta · Sus cuadernos · MCP local · Sin migración de sesiones antiguas").pack(anchor="w", pady=(0, 12))

    frm = ttk.LabelFrame(frame, text="1. Vincular mi propia cuenta Google (una sola vez)", padding=10)
    frm.pack(fill="x")
    project_id = tk.StringVar()
    oauth_file = tk.StringVar()
    profile_id = tk.StringVar(value="personal")
    fields = ttk.Frame(frm)
    fields.pack(fill="x")

    def row(label, variable, index):
        ttk.Label(fields, text=label).grid(column=0, row=index, sticky="w", pady=3)
        entry = ttk.Entry(fields, textvariable=variable, width=65)
        entry.grid(column=1, row=index, sticky="ew", padx=8, pady=3)
        return entry

    row("Nombre de perfil:", profile_id, 0)
    row("Proyecto Google Cloud:", project_id, 1)
    row("Archivo OAuth descargado:", oauth_file, 2)
    fields.columnconfigure(1, weight=1)

    def choose_file():
        selected = filedialog.askopenfilename(title="Seleccionar cliente OAuth Google", filetypes=[("JSON", "*.json")])
        if selected:
            oauth_file.set(selected)

    ttk.Button(fields, text="Buscar JSON", command=choose_file).grid(row=2, column=2, sticky="w")
    hint = ("Requisitos: cuenta Google personal · haber abierto notebook.google.com al menos una vez · "
            "activar notebook.googleapis.com · crear credencial OAuth tipo Aplicación de escritorio.")
    ttk.Label(frm, text=hint, wraplength=810).pack(anchor="w", pady=5)
    ttk.Button(frm, text="Abrir Google Cloud", command=lambda: webbrowser.open("https://console.cloud.google.com/apis/library/notebook.googleapis.com")).pack(side="left", padx=2, pady=5)
    ttk.Button(frm, text="Abrir credenciales OAuth", command=lambda: webbrowser.open("https://console.cloud.google.com/auth/clients")).pack(side="left", padx=2, pady=5)
    ttk.Button(frm, text="Abrir Notebook", command=lambda: webbrowser.open("https://notebook.google.com/")).pack(side="left", padx=2, pady=5)

    status = tk.StringVar(value="No se ha iniciado ninguna operación.")
    ttk.Label(frame, textvariable=status).pack(anchor="w", pady=(10, 3))
    output = scrolledtext.ScrolledText(frame, height=16, wrap="word", state="disabled")
    output.pack(fill="both", expand=True)

    def show(value):
        txt = json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.insert("1.0", txt)
        output.configure(state="disabled")

    def work(fn):
        def job():
            try:
                val = fn()
            except BridgeError as exc:
                app.after(0, lambda e=str(exc): messagebox.showerror("Notebook Conexión", e))
                app.after(0, lambda: status.set("Se requiere completar o corregir la configuración."))
            except Exception:
                app.after(0, lambda: messagebox.showerror("Notebook Conexión", "Error inesperado. No se muestran detalles sensibles."))
                app.after(0, lambda: status.set("Error interno"))
            else:
                app.after(0, lambda: show(val))
                app.after(0, lambda: status.set("Operación completada"))
        status.set("Ejecutando en esta estación...")
        threading.Thread(target=job, daemon=True).start()

    def current():
        return store.load(profile_id.get())

    def save_profile():
        value = Profile(profile_id.get().strip(), project_id.get().strip(), oauth_file.get().strip())
        _client_secrets(value)
        store.save(value)
        return "Perfil configurado. Ahora pulse Vincular cuenta Google (abre navegador)."

    def prefill():
        if not store.path(profile_id.get()).exists():
            return
        try:
            value = current()
        except BridgeError:
            return
        project_id.set(value.project_id)
        oauth_file.set(value.client_secrets)
        status.set("Perfil existente cargado. No se ha importado ninguna sesión antigua.")

    prefill()

    act = ttk.LabelFrame(frame, text="2. Consultar y proteger", padding=10)
    act.pack(fill="x", pady=10)
    btn1 = ttk.Frame(act)
    btn1.pack(fill="x", pady=4)
    ttk.Button(btn1, text="Guardar mi perfil", command=lambda: work(save_profile)).pack(side="left", padx=3)
    ttk.Button(btn1, text="Vincular Google (solo lectura)", command=lambda: work(lambda: (login(current(), write=False), "Cuenta vinculada. Puede listar cuadernos.")[-1])).pack(side="left", padx=3)
    ttk.Button(btn1, text="Listar mis cuadernos", command=lambda: work(lambda: all_notebooks(NotebookClient(current())))).pack(side="left", padx=3)
    def choose_existing():
        choices = store.list_profiles()
        selected = simpledialog.askstring("Cambiar perfil", "Escriba el perfil que desea cargar: " + ", ".join(choices), parent=app)
        if selected and selected in choices:
            profile_id.set(selected)
            prefill()
    ttk.Button(btn1, text="Cargar perfil existente", command=choose_existing).pack(side="left", padx=3)
    ttk.Button(btn1, text="Exportaciones", command=lambda: webbrowser.open(export_directory().as_uri()) if export_directory().exists() else messagebox.showinfo("Exportaciones", "Los archivos aparecerán en: " + str(export_directory()))).pack(side="left", padx=3)

    btn2 = ttk.Frame(act)
    btn2.pack(fill="x", pady=4)

    def toggle_write(enabled):
        if enabled:
            confirmed = messagebox.askyesno("Autorizar modificaciones", "Esta opción permitirá cambios y envíos desde esta cuenta. ¿Autoriza habilitar la política de escritura local?")
            if not confirmed:
                return
        store.enable_write(profile_id.get(), enabled, "CONFIRMO-ESCRITURA" if enabled else "")
        status.set("Permiso de cambios: " + ("ACTIVO. Vincule Google con alcance de escritura." if enabled else "DESACTIVADO."))

    ttk.Button(btn2, text="Habilitar cambios", command=lambda: toggle_write(True)).pack(side="left", padx=3)
    ttk.Button(btn2, text="Bloquear cambios", command=lambda: toggle_write(False)).pack(side="left", padx=3)
    ttk.Button(btn2, text="Vincular Google para cambios", command=lambda: work(lambda: (login(current(), write=True), "OAuth de escritura vinculado")[-1])).pack(side="left", padx=3)
    def set_key():
        key = simpledialog.askstring("Gemini API", "Introduzca su propia clave de AI Studio:", show="*", parent=app)
        if key:
            set_secret(current().name, "gemini-api-key", key.strip())
            status.set("Clave Gemini guardada en almacén seguro del equipo.")
    ttk.Button(btn2, text="Configurar Gemini API", command=set_key).pack(side="left", padx=3)

    gate = ttk.Frame(act)
    gate.pack(fill="x", pady=4)
    def temporary_permission(action):
        label = "modificaciones de cuadernos" if action == "write" else "envío de contenidos a Gemini API"
        if not messagebox.askyesno("Autorización temporal", f"¿Autoriza {label} desde agentes durante 10 minutos? Verifique luego las acciones solicitadas en su agente."):
            return
        from .grants import grant
        try:
            grant(current().name, action, minutes=10)
        except BridgeError as exc:
            messagebox.showerror("Notebook Conexión", str(exc))
            return
        status.set(f"Permiso temporal activado: {label} (10 minutos).")
    ttk.Button(gate, text="Permitir cambios MCP: 10 min", command=lambda: temporary_permission("write")).pack(side="left", padx=3)
    ttk.Button(gate, text="Permitir Gemini MCP: 10 min", command=lambda: temporary_permission("gemini")).pack(side="left", padx=3)
    def close_permissions():
        from .grants import revoke
        try:
            revoke(current().name)
        except BridgeError as exc:
            messagebox.showerror("Notebook Conexión", str(exc))
            return
        status.set("Permisos temporales revocados.")
    ttk.Button(gate, text="Revocar permisos", command=close_permissions).pack(side="left", padx=3)

    agents = ttk.LabelFrame(frame, text="3. Usar lenguaje natural con Claude Code o Codex", padding=10)
    agents.pack(fill="x")
    ttk.Label(agents, text="Primero instala el agente por separado. Al conectar, el MCP local usará este perfil y ningún token se copia al agente.", wraplength=850).pack(anchor="w", pady=(0, 7))
    arow = ttk.Frame(agents)
    arow.pack(fill="x")

    def add_agent(agent):
        if not messagebox.askyesno("Configurar agente", "¿Autoriza modificar la configuración MCP de " + agent.title() + " para habilitar Notebook Conexión en modo SOLO LECTURA?"):
            return
        from .agent_install import configure
        work(lambda: "\n".join(configure(agent, profile=current().name)))

    ttk.Button(arow, text="Conectar Claude Code (lectura)", command=lambda: add_agent("claude")).pack(side="left", padx=3)
    ttk.Button(arow, text="Conectar Codex (lectura)", command=lambda: add_agent("codex")).pack(side="left", padx=3)
    def open_brain():
        from .brain_scope import ScopeStore, Binding
        from .second_brain import SecondBrain
        from pathlib import Path
        window = tk.Toplevel(app)
        window.title("Notebook Conexión — Segundo Cerebro | alcance privado")
        window.geometry("940x650")
        window.minsize(720, 490)
        mainfrm = ttk.Frame(window, padding=12)
        mainfrm.pack(fill="both", expand=True)
        ttk.Label(mainfrm, text="Seleccione exclusivamente los cuadernos autorizados", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(mainfrm, text="Se cargan los cuadernos de cada perfil Google ya vinculado. Selección múltiple Ctrl/Clic o Mayús/Clic.", wraplength=830).pack(anchor="w", pady=4)
        columns = ("perfil", "cuaderno", "titulo")
        tree = ttk.Treeview(mainfrm, columns=columns, show="headings", selectmode="extended", height=10)
        for c, width in [("perfil",120),("cuaderno",370),("titulo",370)]:
            tree.heading(c,text=c.upper())
            tree.column(c,width=width,stretch=True)
        tree.pack(fill="both", expand=True, pady=6)
        foot = tk.StringVar(value="Inicie 'Cargar cuentas' para listar todos los cuadernos.")
        ttk.Label(mainfrm,textvariable=foot, wraplength=850).pack(anchor="w")
        bar1 = ttk.Frame(mainfrm)
        bar1.pack(fill="x",pady=4)
        bar2 = ttk.Frame(mainfrm)
        bar2.pack(fill="x",pady=4)
        scopes = ScopeStore(profiles=store)
        def load_accounts():
            foot.set("Consultando exclusivamente los catálogos de las cuentas configuradas...")
            def job():
                gathered=[]
                errs=[]
                for pname in store.list_profiles():
                    try:
                        prof=store.load(pname)
                        for notebook in all_notebooks(NotebookClient(prof)):
                            gathered.append((pname,notebook["name"],notebook.get("displayName", "")))
                    except Exception:
                        errs.append(pname + ": no disponible / OAuth pendiente")
                def update():
                    tree.delete(*tree.get_children())
                    for item in gathered:
                        tree.insert("", "end", values=item)
                    foot.set(f"{len(gathered)} cuadernos encontrados. " + "; ".join(errs))
                window.after(0,update)
            threading.Thread(target=job,daemon=True).start()
        def save_selection():
            choices = []
            for item in tree.selection():
                p, n, _t = tree.item(item,"values")
                choices.append(Binding(p,n))
            if not choices:
                messagebox.showwarning("Alcance", "Seleccione al menos un cuaderno en la lista.", parent=window)
                return
            if not messagebox.askyesno("Confirmar alcance", f"¿Restringir TODAS las consultas MCP a estos {len(choices)} cuadernos? El agente no podrá ampliar esta selección.", parent=window):
                return
            try:
                scopes.set(choices)
                foot.set(f"Modo ESTRICTO activado: {len(choices)} cuadernos de {len(set(x.profile for x in choices))} cuentas.")
            except BridgeError as exc:
                messagebox.showerror("Alcance", str(exc), parent=window)
        def brain_work(fn):
            def job():
                try:
                    result=fn()
                except BridgeError as exc:
                    window.after(0,lambda text=str(exc): messagebox.showerror("Segundo cerebro",text,parent=window))
                except Exception:
                    window.after(0,lambda: messagebox.showerror("Segundo cerebro","Error inesperado; no se muestran datos sensibles.",parent=window))
                else:
                    window.after(0, lambda: show(result))
            threading.Thread(target=job,daemon=True).start()
        def selected_one():
            bindings=scopes.active()
            options=[x.key for x in bindings]
            choice=simpledialog.askstring("Cuaderno autorizado", "Escriba un perfil|notebooks/UUID de la siguiente lista:\n" + "\n".join(options[:20]), parent=window)
            if not choice or choice not in options:
                raise BridgeError("Debe elegir exactamente uno de los cuadernos autorizados.")
            return next(x for x in bindings if x.key == choice)
        def import_document():
            try:
                binding=selected_one()
            except BridgeError as exc:
                messagebox.showerror("Importación", str(exc), parent=window)
                return
            file=filedialog.askopenfilename(parent=window,title="Seleccione documento, chat o recurso exportado")
            if not file:
                return
            kind=simpledialog.askstring("Tipo documental", "Indique source, chat_export, note_export o artifact_export", initialvalue="source", parent=window)
            if kind not in {"source","chat_export","note_export","artifact_export"}:
                return
            brain_work(lambda:SecondBrain().import_local(binding,Path(file),kind=kind))
        ttk.Button(bar1,text="Cargar cuentas",command=load_accounts).pack(side="left",padx=2)
        ttk.Button(bar1,text="Guardar selección estricta",command=save_selection).pack(side="left",padx=2)
        ttk.Button(bar1,text="Ver selección actual",command=lambda:show(SecondBrain().status())).pack(side="left",padx=2)
        ttk.Button(bar1,text="Sincronizar metadatos",command=lambda:brain_work(lambda: SecondBrain().sync())).pack(side="left",padx=2)
        def sync_text():
            if messagebox.askyesno("Recuperar texto", "¿Desea indexar texto de las fuentes autorizadas cuando la API de Google lo entregue? Otros recursos quedarán solo como metadatos.", parent=window):
                brain_work(lambda:SecondBrain().sync(include_text=True))
        ttk.Button(bar1,text="Indexar texto desde Google",command=sync_text).pack(side="left",padx=2)
        ttk.Button(bar2,text="Importar archivo",command=import_document).pack(side="left",padx=2)
        ttk.Button(bar2,text="Auditar fuentes",command=lambda:brain_work(lambda:SecondBrain().audit_sources())).pack(side="left",padx=2)
        ttk.Button(bar2,text="Comparar cuadernos",command=lambda:brain_work(lambda:SecondBrain().audit_notebooks())).pack(side="left",padx=2)
        def query():
            q=simpledialog.askstring("Consulta estricta", "Pregunta para responder SOLO con evidencia autorizada:", parent=window)
            if q:
                brain_work(lambda:SecondBrain().answer(q))
        ttk.Button(bar2,text="Consultar evidencias",command=query).pack(side="left",padx=2)
        ttk.Button(bar2,text="Cerrar",command=window.destroy).pack(side="right",padx=2)
    ttk.Button(arow, text="Abrir Segundo Cerebro", command=open_brain).pack(side="left", padx=3)
    ttk.Button(arow, text="Cerrar", command=app.destroy).pack(side="right", padx=3)
    ttk.Label(frame, text="Las instrucciones en lenguaje natural se escriben en Claude Code o Codex, no en este panel. Para activar escrituras MCP use Conectar_Agentes_WINDOWS.cmd con permisos explícitos.", wraplength=850).pack(anchor="w", pady=7)

    app.mainloop()

if __name__ == "__main__":
    main()
