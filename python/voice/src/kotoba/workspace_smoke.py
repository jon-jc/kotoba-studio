"""Owned-home desktop smoke for workspace selection and collapsed-rail geometry."""
import json
import os
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


def verify(window):
    """Drive actual rendered controls against the bundled runtime; never run on user data."""
    if not os.environ.get("KOTOBA_HOME") or not os.environ.get("KOTOBA_WORKSPACE_REPORT"):
        raise RuntimeError("Workspace verification requires an isolated home and report path")
    target = window.voice.home / "workspace-smoke-日本語"
    target.mkdir(exist_ok=True)
    report = Path(os.environ["KOTOBA_WORKSPACE_REPORT"])
    state = {"phase": "boot", "pending": False, "done": False}
    evidence = {}
    window.voice.set_locale("en")
    timer = QTimer(window)
    timer.setInterval(150)
    deadline = QTimer(window)
    deadline.setSingleShot(True)

    def finish(error=None):
        if state["done"]:
            return
        state["done"] = True
        timer.stop()
        deadline.stop()
        report.write_text(json.dumps({"ok": error is None, "error": error, **evidence}), encoding="utf-8")
        window.request_quit()
        QApplication.instance().exit(0 if error is None else 1)

    def advance(phase, script):
        state["phase"] = phase
        window.web.page().runJavaScript(script)

    def received(raw):
        state["pending"] = False
        if state["done"] or not raw:
            return
        view = json.loads(raw)
        if "Failed to load plugins" in view["text"]:
            finish("Plugin composition failed")
            return
        if view["alerts"]:
            finish("Folder browser reported an error: " + str(view["alerts"]))
            return
        phase = state["phase"]
        click = "[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')===%s)?.click()"
        if phase == "boot":
            window.web.page().runJavaScript("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Configure later')?.click()")
            if view["add"] and not view["dialog"]:
                advance("wide", click % json.dumps("Add workspace"))
        elif phase == "wide" and "Select Workspace Directory" in view["dialog"]:
            evidence["expanded_picker"] = True
            advance("cancel", "[...document.querySelectorAll('[role=dialog] button')].find(b=>b.textContent.trim()==='Cancel')?.click()")
        elif phase == "cancel" and not view["dialog"]:
            advance("rail", click % json.dumps("Collapse sidebar"))
        elif phase == "rail" and view["rail"]:
            centers = view["centers"]
            if len(centers) != 4 or max(centers) - min(centers) > 1:
                return  # Wait until the collapse transition settles.
            evidence["rail_icon_centers"] = centers
            window.grab().save(str(report.with_suffix('.png')))
            advance("rail-picker", click % json.dumps("Add workspace"))
        elif phase == "rail-picker" and "Select Workspace Directory" in view["dialog"]:
            evidence["collapsed_picker"] = True
            advance("edit", click % json.dumps("Edit path"))
        elif phase == "edit" and view["pathInput"]:
            advance("typed", """(() => { const input=document.querySelector('input[aria-label="Edit path"]');
              Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,%s);
              input.dispatchEvent(new Event('input',{bubbles:true})); })();""" % json.dumps(str(target)))
        elif phase == "typed":
            advance("navigate", "document.querySelector('input[aria-label=\"Edit path\"]')?.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))")
        elif phase == "navigate" and not view["pathInput"] and target.name in view["dialog"] and not view["loading"]:
            advance("adopt", "[...document.querySelectorAll('[role=dialog] button')].find(b=>b.textContent.trim()==='Open')?.click()")
        elif phase == "adopt" and not view["dialog"] and target.name in view["text"]:
            evidence["workspace_adopted"] = True
            window.voice.set_locale("ja")
            state["phase"] = "japanese-ready"
        elif phase == "japanese-ready" and view["jaAdd"]:
            advance("japanese", click % json.dumps("ワークスペースを追加"))
        elif phase == "japanese" and "作業フォルダーを選択" in view["dialog"]:
            evidence["japanese_picker"] = True
            finish()

    def poll():
        if state["pending"] or state["done"]:
            return
        state["pending"] = True
        window.web.page().runJavaScript("""JSON.stringify((() => {
          const buttons=[...document.querySelectorAll('button')];
          const find=label=>buttons.find(b=>b.getAttribute('aria-label')===label);
          const rail=find('Open sidebar');
          const icons=rail ? [rail,find('New session'),find('Add workspace'),find('Search sessions')] : [];
          return {text:document.body.innerText,dialog:document.querySelector('[role=dialog]')?.textContent||'',
            alerts:[...document.querySelectorAll('[role=dialog] [role=alert]')].map(x=>x.textContent).filter(Boolean),
            add:!!find('Add workspace'),jaAdd:!!find('ワークスペースを追加'),rail:!!rail,
            centers:icons.map(b=>[...b?.querySelectorAll('svg,img')||[]].map(x=>x.getBoundingClientRect()).find(r=>r.width>0)).filter(Boolean).map(r=>r.x+r.width/2),
            pathInput:!!document.querySelector('input[aria-label="Edit path"]'),
            loading:!!document.querySelector('[role=dialog] [role=status]')}; })())""", received)

    timer.timeout.connect(poll)
    deadline.timeout.connect(lambda: finish("Timed out in " + state["phase"]))
    deadline.start(60000)
    timer.start()
