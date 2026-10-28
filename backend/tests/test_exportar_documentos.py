from io import BytesIO
from zipfile import ZipFile

import pdfplumber
import pytest

from app.exportar.documento import exportar_documento, FormulaInvalida
from app.silabo.contexto import contexto_clase
from tests.test_exportar_html import _item, _recurso
from tests.test_exportar_html import entorno  # noqa: F401
from tests.test_generacion_api import HEADERS, compartir


@pytest.mark.parametrize('formato', ['pdf', 'docx'])
def test_documento_preguntas_respuestas_y_formula(silabo, formato):
    r = _recurso('cuestionario', [_item(1, 'Calcula $x^2 + \\frac{1}{2}$')])
    datos = exportar_documento(r, contexto_clase(silabo, 'M2-S1'), formato)
    if formato == 'pdf':
        with pdfplumber.open(BytesIO(datos)) as pdf:
            texto = '\n'.join(p.extract_text() or '' for p in pdf.pages)
            assert len(pdf.pages) >= 2
    else:
        with ZipFile(BytesIO(datos)) as z:
            texto = z.read('word/document.xml').decode()
            assert any(n.startswith('word/media/') for n in z.namelist())
            assert not any(b'TargetMode="External"' in z.read(n) for n in z.namelist() if n.endswith('.rels'))
    assert texto.index('Calcula') < texto.index('Respuestas y justificaciones')
    assert 'M2-S1' in texto and 'revisado por el docente' in texto
    assert 'item_id' not in texto


def test_formula_invalida_controlada(silabo):
    r = _recurso('cuestionario', [_item(1, '$\\comandoNoPermitido{x}$')])
    with pytest.raises(FormulaInvalida):
        exportar_documento(r, contexto_clase(silabo, 'M2-S1'), 'pdf')


@pytest.mark.parametrize('expresion', ['x'*501, '{'*41+'x'+'}'*41, r'\input{secreto}'])
def test_limites_formulas(silabo, expresion):
    r = _recurso('cuestionario', [_item(1, '$'+expresion+'$')])
    with pytest.raises(FormulaInvalida):
        exportar_documento(r, contexto_clase(silabo, 'M2-S1'), 'docx')


def test_preguntas_no_dejan_opciones_solas(silabo):
    r = _recurso('cuestionario', [_item(n, r'Calcula $\sqrt{x}$ e interpreta.') for n in range(1, 9)])
    with pdfplumber.open(BytesIO(exportar_documento(r, contexto_clase(silabo, 'M2-S1'), 'pdf'))) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ''
            if 'Respuestas y justificaciones' in texto:
                break
            assert texto.count('Pregunta ') == texto.count('D) Opción 3')


@pytest.mark.parametrize('formato', ['pdf', 'docx'])
def test_marcado_se_exporta_como_texto(silabo, formato):
    marca = '<img src="https://example.invalid/privado">'
    datos = exportar_documento(_recurso('cuestionario', [_item(1, marca)]), contexto_clase(silabo, 'M2-S1'), formato)
    if formato == 'pdf':
        with pdfplumber.open(BytesIO(datos)) as pdf:
            assert marca in '\n'.join(p.extract_text() or '' for p in pdf.pages)
    else:
        with ZipFile(BytesIO(datos)) as z:
            assert '&lt;img' in z.read('word/document.xml').decode()
            assert not any(b'TargetMode="External"' in z.read(n) for n in z.namelist() if n.endswith('.rels'))


@pytest.mark.parametrize('formato,mime', [('pdf', 'application/pdf'), ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')])
def test_api_documentos(entorno, formato, mime):
    _, clientes, d, aid, producir = entorno
    recurso = producir()
    url = f"/asignaturas/{aid}/recursos/{recurso['id']}/exportar?formato={formato}"
    assert d.get(url).status_code == 409
    assert clientes('ajeno@uti.edu.ec').get(url).status_code in (403, 404)
    assert d.post(f"/asignaturas/{aid}/recursos/{recurso['id']}/validar", json={'revision': recurso['revision']}, headers=HEADERS).status_code == 200
    respuesta = d.get(url)
    assert respuesta.status_code == 200
    assert respuesta.headers['content-type'] == mime
    assert respuesta.headers['content-disposition'].endswith(f'.{formato}"')
    assert respuesta.content.startswith(b'%PDF' if formato == 'pdf' else b'PK')
    contenido = recurso['contenido']
    contenido[0]['pregunta'] = '¿Qué procedimiento corresponde al contexto descrito en esta pregunta editada?'
    editado = d.put(f"/asignaturas/{aid}/recursos/{recurso['id']}", json={'revision': recurso['revision'], 'contenido': contenido}, headers=HEADERS)
    assert editado.status_code == 200
    assert d.get(url).status_code == 409


@pytest.mark.parametrize('formato', ['pdf', 'docx'])
def test_tablas_y_texto_literal(silabo, formato):
    from app.herramientas.sin_ia import generar_sin_ia
    from app.silabo.contexto import contexto_por_id
    r = _recurso('hoja_ruta', generar_sin_ia('hoja_ruta', silabo, 'asignatura'), 'asignatura')
    datos = exportar_documento(r, contexto_por_id(silabo, 'asignatura'), formato)
    if formato == 'docx':
        from docx import Document
        assert Document(BytesIO(datos)).tables
    else:
        with pdfplumber.open(BytesIO(datos)) as pdf:
            assert 'Calendario' in '\n'.join(p.extract_text() or '' for p in pdf.pages)


@pytest.mark.parametrize('formato', ['html', 'pdf', 'docx'])
def test_lector_descarga_solo_validado_y_pertenencia(entorno, silabo, formato):
    app, clientes, d, aid, producir = entorno
    recurso = producir()
    lector = clientes('lector@uti.edu.ec')
    assert compartir(d, aid, 'lector@uti.edu.ec', 'lector').status_code == 200
    url = f"/asignaturas/{aid}/recursos/{recurso['id']}/exportar?formato={formato}"
    assert lector.get(url).status_code == 409
    assert d.post(f"/asignaturas/{aid}/recursos/{recurso['id']}/validar", json={'revision': recurso['revision']}, headers=HEADERS).status_code == 200
    assert lector.get(url).status_code == 200
    from app.silabo.modelo import SilaboUTI
    datos = silabo.model_dump()
    datos['proyecto_formativo']['codigo'] += '-OTRO'
    otro = app.state.asignaturas.guardar('dueno@uti.edu.ec', SilaboUTI.model_validate(datos))['id']
    assert otro != aid
    assert d.get(f"/asignaturas/{otro}/recursos/{recurso['id']}/exportar?formato={formato}").status_code == 404
    lector.cookies.clear()
    assert lector.get(url).status_code == 401
