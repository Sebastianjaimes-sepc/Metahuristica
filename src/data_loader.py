"""Data loader for AMPL .dat instances used in the GA routing project.
Provides:
- parse_ampl_dat(path) -> dict of raw params
- build_instance(parsed) -> Instance dataclass with typed structures

The parser is tolerant to the specific .dat formatting used in the provided instance file.
"""
from dataclasses import dataclass
from typing import Dict, Any
import re
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dataclass
class Client:
    id: int
    escliente: int
    esdepo: int
    escritico: int
    DemE: float = 0.0
    DemR: float = 0.0
    TS: float = 0.0
    MinDC: float = 0.0
    MaxDC: float = 24.0

@dataclass
class Truck:
    id: int
    Cap: float
    CH: float
    CF6: float
    CF12: float
    esHora: int = 1
    esF6: int = 0
    esF12: int = 0

@dataclass
class Instance:
    clients: Dict[int, Client]
    trucks: Dict[int, Truck]
    Dist: np.ndarray
    tvia: Dict[int, np.ndarray]
    v: Dict[int, float]
    tinic: Dict[int, float]
    tfin: Dict[int, float]
    params: Dict[str, Any]

    def n_nodes(self):
        return len(self.clients)

# ------------------------------------------------------
# Lightweight AMPL .dat parser
# ------------------------------------------------------

def _numtok(s: str):
    s = s.strip()
    if re.match(r"^-?\d+$", s):
        return int(s)
    try:
        return float(s)
    except ValueError:
        return s


def _tokenize_pairs(body: str):
    toks = [t for t in re.split(r"\s+", body.strip()) if t != ""]
    if len(toks) == 0:
        return {}
    if len(toks) == 1:
        return _numtok(toks[0])
    # pairs index value
    if len(toks) % 2 == 0:
        d = {}
        for i in range(0, len(toks), 2):
            idx = _numtok(toks[i])
            val = _numtok(toks[i+1])
            d[idx] = val
        return d
    # fallback
    return toks


def parse_matrix_param(header: str, body: str):
    header = header.lstrip(":").strip()
    cols = [int(x) for x in re.split(r"\s+", header) if x != ""]
    mat = {}
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p for p in re.split(r"\s+", line) if p != ""]
        row = int(parts[0])
        vals = [float(x) for x in parts[1:1+len(cols)]]
        for c_idx, col in enumerate(cols):
            mat[(row, col)] = vals[c_idx]
    n = max([i for i,_ in mat.keys()])
    m = max([j for _,j in mat.keys()])
    arr = np.zeros((n+1, m+1), dtype=float)
    for (i,j),v in mat.items():
        arr[i,j]=v
    return arr


def parse_tvia(body: str):
    blocks = {}
    block_pattern = re.compile(r"\[\*,\*,(\d+)\]:\s*(.*?)\s*:=\s*([\s\S]*?)(?=(\[\*,\*,\d+\]:)|$)", re.IGNORECASE)
    for bm in block_pattern.finditer(body):
        f = int(bm.group(1))
        header = bm.group(2).strip()
        block_body = bm.group(3).strip()
        cols = [int(x) for x in re.split(r"\s+", header) if x != ""]
        mat = {}
        for line in block_body.splitlines():
            line=line.strip()
            if not line:
                continue
            parts = [p for p in re.split(r"\s+", line) if p != ""]
            row = int(parts[0])
            vals = [float(x) for x in parts[1:1+len(cols)]]
            for c_idx, col in enumerate(cols):
                mat[(row, col)] = vals[c_idx]
        n = max([i for i,_ in mat.keys()])
        m = max([j for _,j in mat.keys()])
        arr = np.zeros((n+1, m+1), dtype=float)
        for (i,j),v in mat.items():
            arr[i,j]=v
        blocks[f]=arr
    return blocks


def parse_param_blocks(text: str):
    res = {}
    text = re.sub(r"#.*", "", text)
    for m in re.finditer(r"param\s+(\w+)\b(.*?)\s*:=\s*([\s\S]*?)\s*;", text, re.IGNORECASE):
        name = m.group(1)
        header = m.group(2).strip()
        body = m.group(3).strip()
        if header.startswith(":"):
            res[name] = parse_matrix_param(header, body)
        elif name.lower() == 'tvia' or body.strip().startswith('[*,*,'):
            res[name] = parse_tvia(body)
        else:
            res[name] = _tokenize_pairs(body)
    return res


def parse_ampl_dat(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    return parse_param_blocks(text)


# ------------------------------------------------------
# builder
# ------------------------------------------------------
REQUIRED_PARAMS = ['escliente','esdepo','escritico','esHora','esF6','esF12','Cap','CH','CF6','CF12','DemE','DemR','TS','MinDC','MaxDC','Dist','tvia','v','tinic','tfin','nmuelles','durH','Lc','tcarga']


def build_instance(parsed: dict) -> Instance:
    missing = [p for p in REQUIRED_PARAMS if p not in parsed]
    if missing:
        raise ValueError(f"Faltan parámetros requeridos en .dat: {missing}")

    escliente = parsed['escliente'] if isinstance(parsed['escliente'], dict) else {}
    esdepo = parsed['esdepo'] if isinstance(parsed['esdepo'], dict) else {}
    escritico = parsed['escritico'] if isinstance(parsed['escritico'], dict) else {}

    all_node_ids = sorted(set(list(escliente.keys()) + list(esdepo.keys())))
    clients = {}
    for nid in all_node_ids:
        clients[nid] = Client(
            id=nid,
            escliente=int(escliente.get(nid,0)),
            esdepo=int(esdepo.get(nid,0)),
            escritico=int(escritico.get(nid,0)),
            DemE=float(parsed['DemE'].get(nid,0.0)),
            DemR=float(parsed['DemR'].get(nid,0.0)),
            TS=float(parsed['TS'].get(nid,0.0)),
            MinDC=float(parsed['MinDC'].get(nid,0.0)),
            MaxDC=float(parsed['MaxDC'].get(nid,24.0)),
        )

    Cap = parsed['Cap']
    CH = parsed['CH']
    CF6 = parsed['CF6']
    CF12 = parsed['CF12']
    esHora = parsed['esHora'] if isinstance(parsed['esHora'], dict) else {}
    esF6 = parsed['esF6'] if isinstance(parsed['esF6'], dict) else {}
    esF12 = parsed['esF12'] if isinstance(parsed['esF12'], dict) else {}

    truck_ids = sorted(set(list(Cap.keys())))
    trucks = {}
    for tid in truck_ids:
        trucks[tid] = Truck(
            id=tid,
            Cap=float(Cap.get(tid)),
            CH=float(CH.get(tid)),
            CF6=float(CF6.get(tid)),
            CF12=float(CF12.get(tid)),
            esHora=int(esHora.get(tid,1)),
            esF6=int(esF6.get(tid,0)),
            esF12=int(esF12.get(tid,0)),
        )

    Dist = parsed['Dist'] if isinstance(parsed['Dist'], np.ndarray) else np.array([])
    tvia = parsed['tvia'] if isinstance(parsed['tvia'], dict) else {}
    v = {int(k): float(v) for k,v in parsed['v'].items()} if isinstance(parsed['v'], dict) else {}
    tinic = {int(k): float(v) for k,v in parsed['tinic'].items()} if isinstance(parsed['tinic'], dict) else {}
    tfin = {int(k): float(v) for k,v in parsed['tfin'].items()} if isinstance(parsed['tfin'], dict) else {}

    params = {k:v for k,v in parsed.items() if k not in ['escliente','esdepo','escritico','Cap','CH','CF6','CF12','DemE','DemR','TS','MinDC','MaxDC','Dist','tvia','v','tinic','tfin']}

    inst = Instance(clients=clients, trucks=trucks, Dist=Dist, tvia=tvia, v=v, tinic=tinic, tfin=tfin, params=params)

    # Basic consistency checks
    n_nodes = len(clients)
    if Dist.size and (Dist.shape[0] != n_nodes or Dist.shape[1] != n_nodes):
        logger.warning(f"Dist matrix shape {Dist.shape} does not match number of nodes {n_nodes}")
    if len(tvia) == 0:
        logger.warning("tvia not parsed as blocks per franja; check file format")

    return inst


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Quick tester for data_loader')
    parser.add_argument('--dat', required=True)
    args = parser.parse_args()
    parsed = parse_ampl_dat(args.dat)
    inst = build_instance(parsed)
    print('Loaded instance: nodes=', inst.n_nodes(), 'trucks=', len(inst.trucks))
