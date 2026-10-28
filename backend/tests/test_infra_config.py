"""Regresiones de aislamiento del despliegue, sin arrancar Docker."""
from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parents[2]


def test_solo_proxy_publica_puertos_y_sin_volumen_de_desarrollo():
    compose = yaml.safe_load((RAIZ/'infra/compose.yaml').read_text(encoding='utf-8'))
    for nombre, servicio in compose['services'].items():
        assert not servicio.get('privileged')
        assert not servicio.get('container_name')
        if nombre != 'proxy':
            assert not servicio.get('ports'), nombre
    assert set(compose['volumes']) == {'datos'}
    assert 'external' not in compose['volumes']['datos']
    assert compose['networks']['datos']['internal']
    for nombre in ('api','worker','web','proxy'):
        s = compose['services'][nombre]
        assert s['read_only'] and s['cap_drop'] == ['ALL']


def test_proxy_alcanzable_y_solo_el():
    """Con solo redes internas Docker no publica puertos; la red pública es exclusiva del proxy."""
    compose = yaml.safe_load((RAIZ/'infra/compose.yaml').read_text(encoding='utf-8'))
    redes = compose['networks']
    for nombre, servicio in compose['services'].items():
        if servicio.get('ports'):
            assert any(not (redes[r] or {}).get('internal') for r in servicio['networks']), nombre
    assert [n for n, s in compose['services'].items() if 'publica' in s.get('networks', [])] == ['proxy']
    assert compose['networks']['borde']['ipam']['config'][0]['ip_range']


def test_copia_imagen_no_incluye_entorno_o_silabos_reales():
    dockerignore = (RAIZ/'.dockerignore').read_text(encoding='utf-8')
    assert dockerignore.splitlines()[1] == '**'
    assert '!Silabos' not in dockerignore and '!docs/**' not in dockerignore
    assert '**/.env*' in dockerignore
    backend = (RAIZ/'infra/Dockerfile.backend').read_text(encoding='utf-8')
    assert 'COPY . ' not in backend
    assert '@sha256:' in backend
    assert 'USER 10001:10001' in backend


def test_tmpfs_es_una_sola_entrada_por_servicio():
    """En estilo de flujo YAML la coma de «size=…,mode=…» parte la entrada en dos y Docker la rechaza."""
    compose = yaml.safe_load((RAIZ/'infra/compose.yaml').read_text(encoding='utf-8'))
    for nombre, servicio in compose['services'].items():
        for entrada in servicio.get('tmpfs', []):
            assert entrada.startswith('/'), nombre


def test_nginx_no_escribe_fuera_de_tmp():
    """Con read_only, nginx no arranca si algún temporal queda en /var/cache/nginx."""
    for nombre in ('web.conf', 'proxy.conf.template'):
        conf = (RAIZ/'infra/nginx'/nombre).read_text(encoding='utf-8')
        for temporal in ('client_body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'):
            assert f'{temporal}_temp_path /tmp/' in conf, (nombre, temporal)


def test_imagen_web_incluye_los_recursos_publicos():
    """Vite copia frontend/public (favicon y logo UTI); excluirlo deja la interfaz sin marca."""
    dockerignore = (RAIZ/'.dockerignore').read_text(encoding='utf-8').splitlines()
    assert '!frontend/public/**' in dockerignore
    assert all((RAIZ/'frontend/public'/nombre).is_file() for nombre in ('favicon.svg', 'logo-uti.png'))


def test_proxy_no_confia_cabeceras_de_cliente_y_no_registra_uri():
    nginx = (RAIZ/'infra/nginx/proxy.conf.template').read_text(encoding='utf-8')
    assert 'proxy_set_header X-Forwarded-For $remote_addr;' in nginx
    assert '$proxy_add_x_forwarded_for' not in nginx
    assert 'access_log off;' in nginx
    assert 'location ^~ /api/salud/ { return 404; }' in nginx
    assert 'client_max_body_size 10m;' in nginx
    assert 'proxy_hide_header Cache-Control;' in nginx
