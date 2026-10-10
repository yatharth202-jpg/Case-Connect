import os
import sys
import json
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from faker import Faker
import openpyxl
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent

class SyntheticDataGenerator:
    """
    Deterministic synthetic data generator for Case Connect AI.
    Generates multi-scenario, multi-format test data with ground_truth.json.
    """
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.fake = Faker(locale="en_IN")
        self.fake.seed_instance(seed)
        Faker.seed(seed)

    def generate_phone(self) -> str:
        first_digit = self.rng.choice(["6", "7", "8", "9"])
        rest = "".join(self.rng.choices("0123456789", k=9))
        return f"{first_digit}{rest}"

    def generate_account(self) -> str:
        prefix = self.rng.choice(["10", "20", "30", "50", "90"])
        rest = "".join(self.rng.choices("0123456789", k=10))
        return f"{prefix}{rest}"

    def generate_vehicle(self) -> str:
        state = self.rng.choice(["DL", "UP", "HR", "MH", "KA"])
        rto = f"{self.rng.randint(1, 14):02d}"
        series = self.rng.choice(["AB", "CD", "EF", "GH", "JK"])
        num = f"{self.rng.randint(1000, 9999)}"
        return f"{state}{rto}{series}{num}"

    def generate_ip(self) -> str:
        return f"203.0.{self.rng.randint(100, 200)}.{self.rng.randint(1, 254)}"

    def build_scenario_data(self, scenario: str, size: str) -> dict:
        scale_multipliers = {"small": 1, "medium": 5, "large": 20}
        mult = scale_multipliers.get(size, 1)

        base_date = datetime(2026, 8, 1)
        data = {
            "people": [],
            "phones": [],
            "accounts": [],
            "vehicles": [],
            "calls": [],
            "transactions": [],
            "ip_logs": [],
            "sdr": [],
            "account_master": [],
            "firs": [],
            "ground_truth": {}
        }

        planted = {
            "organizers": [],
            "collection_accounts": [],
            "mules": [],
            "recruiters": [],
            "shell_accounts": [],
            "victims": [],
            "chain_entities": [],
            "hub_phone": None,
            "spoke_phones": [],
            "spike_onset_date": None,
            "spike_peak_date": None,
            "spike_peak_calls": 0,
            "decoys": []
        }

        # -------------------------------------------------------------
        # 1. SCENARIO TOPOLOGIES
        # -------------------------------------------------------------

        if scenario == "ring":
            # Single layered ring
            self._build_ring(data, planted, base_date, mult, ring_id=1, include_fir=True)

        elif scenario == "two_rings":
            # Two independent rings
            self._build_ring(data, planted, base_date, mult, ring_id=1, include_fir=True)
            self._build_ring(data, planted, base_date + timedelta(days=2), mult, ring_id=2, include_fir=True)

        elif scenario == "chain":
            # Plain linear layering A -> B -> C -> D -> E -> F (no recruiters, no shell)
            chain_length = 6
            entities = []
            for i in range(chain_length):
                name = f"{self.fake.first_name()} {self.fake.last_name()}"
                phone = self.generate_phone()
                account = self.generate_account()
                entities.append({"step": i + 1, "name": name, "phone": phone, "account": account})
                data["people"].append({"name": name, "phone": phone, "account": account})
            planted["chain_entities"] = entities

            # Transfers: A -> B -> C -> D -> E -> F
            initial_amount = self.rng.randint(30000000, 50000000) # 3L to 5L
            for i in range(chain_length - 1):
                sender = entities[i]
                receiver = entities[i + 1]
                t_date = base_date + timedelta(days=i + 1)
                # Deduct small friction fee
                amount = int(initial_amount * (0.95 ** i))
                data["transactions"].append({
                    "txn_id": f"TXN-CHN-{i+1:03d}",
                    "date": t_date.strftime("%Y-%m-%d"),
                    "time": f"{10 + i}:15:00",
                    "from_account": sender["account"],
                    "from_name": sender["name"],
                    "to_account": receiver["account"],
                    "to_name": receiver["name"],
                    "amount_paise": amount,
                    "reference": f"NEFT-CHN{i+1}-{receiver['name'].replace(' ', '')}-{receiver['account']}"
                })

            # 1-2 calls between adjacent owners
            for i in range(chain_length - 1):
                c_date = base_date + timedelta(days=i + 1)
                data["calls"].append({
                    "call_id": f"CALL-CHN-{i+1:03d}",
                    "caller": entities[i]["phone"],
                    "receiver": entities[i + 1]["phone"],
                    "date": c_date.strftime("%Y-%m-%d"),
                    "time": f"{9 + i}:45:00",
                    "duration_seconds": self.rng.randint(40, 120),
                    "call_type": "out"
                })

        elif scenario == "hub_spoke":
            # Hub phone calling many spokes, NO bank data
            hub_phone = self.generate_phone()
            hub_name = f"{self.fake.first_name()} {self.fake.last_name()}"
            planted["hub_phone"] = {"name": hub_name, "phone": hub_phone}
            num_spokes = 15 * mult
            spokes = []
            for s_idx in range(num_spokes):
                spoke_phone = self.generate_phone()
                spoke_name = f"{self.fake.first_name()} {self.fake.last_name()}"
                spokes.append({"name": spoke_name, "phone": spoke_phone})
                # Call from hub to spoke
                call_day = base_date + timedelta(days=self.rng.randint(1, 10))
                data["calls"].append({
                    "call_id": f"CALL-HUB-{s_idx+1:03d}",
                    "caller": hub_phone,
                    "receiver": spoke_phone,
                    "date": call_day.strftime("%Y-%m-%d"),
                    "time": f"{self.rng.randint(9, 20):02d}:{self.rng.randint(10, 59):02d}:00",
                    "duration_seconds": self.rng.randint(30, 250),
                    "call_type": "out"
                })
            planted["spoke_phones"] = spokes

        elif scenario == "benign_heavy":
            # Decoy call center & shop account (high steady volume, NO fraud ring)
            call_center_phone = self.generate_phone()
            shop_account = self.generate_account()
            planted["decoys"].append({"type": "call_center", "phone": call_center_phone})
            planted["decoys"].append({"type": "shop_account", "account": shop_account})

            for d in range(1, 15):
                day = base_date + timedelta(days=d)
                for c in range(30 * mult):
                    data["calls"].append({
                        "call_id": f"CALL-CC-{d}-{c+1:03d}",
                        "caller": call_center_phone,
                        "receiver": self.generate_phone(),
                        "date": day.strftime("%Y-%m-%d"),
                        "time": f"{self.rng.randint(9, 18):02d}:{self.rng.randint(10, 59):02d}:00",
                        "duration_seconds": self.rng.randint(30, 120),
                        "call_type": "out"
                    })

            for d in range(1, 15):
                day = base_date + timedelta(days=d)
                for t in range(15 * mult):
                    data["transactions"].append({
                        "txn_id": f"TXN-SHOP-{d}-{t+1:03d}",
                        "date": day.strftime("%Y-%m-%d"),
                        "time": "15:30:00",
                        "from_account": self.generate_account(),
                        "from_name": self.fake.first_name(),
                        "to_account": shop_account,
                        "to_name": "Retail Store",
                        "amount_paise": self.rng.randint(20000, 150000),
                        "reference": f"UPI/TXN/{self.rng.randint(10000000,99999999)}/PAY"
                    })

        elif scenario == "cdr_only":
            # Only CDR file: generate a caller community without bank or FIR data
            phones_pool = [self.generate_phone() for _ in range(20 * mult)]
            for idx in range(60 * mult):
                p1 = self.rng.choice(phones_pool)
                p2 = self.rng.choice(phones_pool)
                if p1 != p2:
                    call_day = base_date + timedelta(days=self.rng.randint(1, 10))
                    data["calls"].append({
                        "call_id": f"CALL-CDRONLY-{idx+1:04d}",
                        "caller": p1,
                        "receiver": p2,
                        "date": call_day.strftime("%Y-%m-%d"),
                        "time": f"{self.rng.randint(8, 22):02d}:{self.rng.randint(10, 59):02d}:00",
                        "duration_seconds": self.rng.randint(20, 300),
                        "call_type": self.rng.choice(["out", "in"])
                    })

        elif scenario == "bank_only":
            # Only bank data: layering and transfers without CDR or FIR
            accts_pool = [{"acct": self.generate_account(), "name": self.fake.first_name()} for _ in range(15 * mult)]
            for idx in range(40 * mult):
                a1 = self.rng.choice(accts_pool)
                a2 = self.rng.choice(accts_pool)
                if a1["acct"] != a2["acct"]:
                    t_day = base_date + timedelta(days=self.rng.randint(1, 10))
                    amt = self.rng.randint(500000, 15000000)
                    data["transactions"].append({
                        "txn_id": f"TXN-BANKONLY-{idx+1:04d}",
                        "date": t_day.strftime("%Y-%m-%d"),
                        "time": f"{self.rng.randint(10, 18):02d}:30:00",
                        "from_account": a1["acct"],
                        "from_name": a1["name"],
                        "to_account": a2["acct"],
                        "to_name": a2["name"],
                        "amount_paise": amt,
                        "reference": f"IMPS/{self.rng.randint(1000000,9999999)}/SETTLEMENT"
                    })

        elif scenario == "sparse_tiny":
            # 10 to 40 rows total, 1-2 FIRs
            self._build_sparse_tiny(data, planted, base_date)

        elif scenario == "random_mix":
            # Random counts from wide ranges, random topology
            num_people = self.rng.randint(5, 20)
            num_calls = self.rng.randint(30, 80)
            num_txns = self.rng.randint(15, 50)
            people = [{"name": f"{self.fake.first_name()} {self.fake.last_name()}", "phone": self.generate_phone(), "account": self.generate_account()} for _ in range(num_people)]
            data["people"].extend(people)

            for c in range(num_calls):
                p1 = self.rng.choice(people)
                p2 = self.rng.choice(people)
                if p1["phone"] != p2["phone"]:
                    call_day = base_date + timedelta(days=self.rng.randint(1, 12))
                    data["calls"].append({
                        "call_id": f"CALL-RND-{c+1:04d}",
                        "caller": p1["phone"],
                        "receiver": p2["phone"],
                        "date": call_day.strftime("%Y-%m-%d"),
                        "time": f"{self.rng.randint(9, 21):02d}:{self.rng.randint(10, 59):02d}:00",
                        "duration_seconds": self.rng.randint(20, 200),
                        "call_type": self.rng.choice(["out", "in"])
                    })

            for t in range(num_txns):
                p1 = self.rng.choice(people)
                p2 = self.rng.choice(people)
                if p1["account"] != p2["account"]:
                    t_day = base_date + timedelta(days=self.rng.randint(1, 12))
                    amt = self.rng.randint(100000, 2000000)
                    data["transactions"].append({
                        "txn_id": f"TXN-RND-{t+1:04d}",
                        "date": t_day.strftime("%Y-%m-%d"),
                        "time": "14:00:00",
                        "from_account": p1["account"],
                        "from_name": p1["name"],
                        "to_account": p2["account"],
                        "to_name": p2["name"],
                        "amount_paise": amt,
                        "reference": f"UPI/{self.rng.randint(100000000, 999999999)}/PAY"
                    })

        # -------------------------------------------------------------
        # 2. NOISE INJECTION (Except for strictly isolated scenarios)
        # -------------------------------------------------------------
        # 2. NOISE INJECTION (Except for strictly isolated scenarios)
        # -------------------------------------------------------------
        if scenario not in ["sparse_tiny", "bank_only"]:
            # Shared phone relatives: 2 people with same surname sharing 1 phone
            noise_surname = self.fake.last_name()
            shared_phone = self.generate_phone()
            relative_1 = f"Anil {noise_surname}"
            relative_2 = f"Sunil {noise_surname}"
            data["people"].append({"name": relative_1, "phone": shared_phone})
            data["people"].append({"name": relative_2, "phone": shared_phone})

            # Random background calls
            for i in range(20 * mult):
                data["calls"].append({
                    "call_id": f"CALL-NOISE-{i+1:04d}",
                    "caller": self.generate_phone(),
                    "receiver": self.generate_phone(),
                    "date": (base_date + timedelta(days=self.rng.randint(1, 12))).strftime("%Y-%m-%d"),
                    "time": f"{self.rng.randint(8, 23):02d}:{self.rng.randint(10, 59):02d}:00",
                    "duration_seconds": self.rng.randint(10, 240),
                    "call_type": self.rng.choice(["in", "out", "sms"])
                })

        if scenario not in ["sparse_tiny", "cdr_only", "hub_spoke"]:
            # Random background transactions
            for j in range(15 * mult):
                data["transactions"].append({
                    "txn_id": f"TXN-NOISE-{j+1:04d}",
                    "date": (base_date + timedelta(days=self.rng.randint(1, 12))).strftime("%Y-%m-%d"),
                    "time": "12:00:00",
                    "from_account": self.generate_account(),
                    "from_name": self.fake.first_name(),
                    "to_account": self.generate_account(),
                    "to_name": self.fake.first_name(),
                    "amount_paise": self.rng.randint(100000, 5000000),
                    "reference": f"IMPS/{self.rng.randint(1000000, 9999999)}/TRANSFER"
                })

        # -------------------------------------------------------------
        # 3. DERIVE ENTITY MASTER RECORDS & LOGS
        # -------------------------------------------------------------
        # IP logs for early calls
        for call in data["calls"][:30]:
            data["ip_logs"].append({
                "log_id": f"IP-{call['call_id']}",
                "identifier": call["caller"],
                "ip_address": self.generate_ip(),
                "datetime": f"{call['date']}T{call['time']}Z"
            })

        # SDR records for distinct phones
        distinct_callers = set([c["caller"] for c in data["calls"]] + [c["receiver"] for c in data["calls"]])
        for phone in list(distinct_callers)[:50]:
            data["sdr"].append({
                "phone": phone,
                "subscriber_name": f"{self.fake.first_name()} {self.fake.last_name()}",
                "activation_date": (base_date - timedelta(days=self.rng.randint(30, 300))).strftime("%Y-%m-%d")
            })

        # Account master records
        distinct_accts = set([t["from_account"] for t in data["transactions"]] + [t["to_account"] for t in data["transactions"]])
        for acct in list(distinct_accts)[:50]:
            data["account_master"].append({
                "account_no": acct,
                "holder_name": f"{self.fake.first_name()} {self.fake.last_name()}",
                "registered_mobile": self.generate_phone(),
                "branch": f"{self.fake.city()} Branch",
                "opened_date": (base_date - timedelta(days=self.rng.randint(60, 500))).strftime("%Y-%m-%d")
            })

        # Ground truth structural invariants
        total_volume_paise = sum(t["amount_paise"] for t in data["transactions"])
        distinct_phones = len(distinct_callers)
        distinct_accounts = len(distinct_accts)

        data["ground_truth"] = {
            "seed": self.seed,
            "scenario": scenario,
            "size": size,
            "total_transactions": len(data["transactions"]),
            "total_calls": len(data["calls"]),
            "total_firs": len(data["firs"]),
            "total_volume_paise": total_volume_paise,
            "total_volume_inr": total_volume_paise / 100.0,
            "distinct_phones": distinct_phones,
            "distinct_accounts": distinct_accounts,
            "planted": planted
        }

        return data

    def _build_ring(self, data: dict, planted: dict, base_date: datetime, mult: int, ring_id: int = 1, include_fir: bool = True):
        # 1. Organizer (Appears in ZERO FIRs)
        organizer_name = f"{self.fake.first_name()} {self.fake.last_name()}"
        organizer_phone = self.generate_phone()
        organizer_account = self.generate_account()
        org_entry = {
            "ring_id": ring_id,
            "name": organizer_name,
            "phone": organizer_phone,
            "account": organizer_account
        }
        planted["organizers"].append(org_entry)

        # 2. Collection Account & Shell Account
        collection_acc = self.generate_account()
        collection_holder = f"{self.fake.first_name()} {self.fake.last_name()}"
        planted["collection_accounts"].append({
            "ring_id": ring_id,
            "account": collection_acc,
            "holder": collection_holder
        })

        shell_acc = self.generate_account()
        shell_org = f"{self.fake.company()} Solutions Pvt Ltd"
        planted["shell_accounts"].append({
            "ring_id": ring_id,
            "account": shell_acc,
            "holder": shell_org
        })

        # 3. Victims (3 to 6)
        num_victims = self.rng.randint(3, 6)
        victims = []
        for _ in range(num_victims):
            v_name = f"{self.fake.first_name()} {self.fake.last_name()}"
            v_acc = self.generate_account()
            victims.append({"ring_id": ring_id, "name": v_name, "account": v_acc})
        planted["victims"].extend(victims)

        # 4. Mules (2 to 4)
        num_mules = self.rng.randint(2, 4)
        mules = []
        for _ in range(num_mules):
            m_name = f"{self.fake.first_name()} {self.fake.last_name()}"
            m_phone = self.generate_phone()
            m_acc = self.generate_account()
            mules.append({"ring_id": ring_id, "name": m_name, "phone": m_phone, "account": m_acc})
        planted["mules"].extend(mules)

        # 5. Recruiter
        recruiter_name = f"{self.fake.first_name()} {self.fake.last_name()}"
        recruiter_phone = self.generate_phone()
        recruiter_acc = self.generate_account()
        recruiter_veh = self.generate_vehicle()
        planted["recruiters"].append({
            "ring_id": ring_id,
            "name": recruiter_name,
            "phone": recruiter_phone,
            "account": recruiter_acc,
            "vehicle": recruiter_veh
        })

        # Financial Flow: Victims -> Collection Account
        victim_amount_paise = self.rng.randint(25000000, 35000000) # 2.5L to 3.5L
        total_inflow_paise = 0
        for i, v in enumerate(victims):
            txn_date = base_date + timedelta(days=self.rng.randint(1, 3))
            amount = victim_amount_paise
            total_inflow_paise += amount
            data["transactions"].append({
                "txn_id": f"TXN-VIC-R{ring_id}-{i+1:03d}",
                "date": txn_date.strftime("%Y-%m-%d"),
                "time": "11:20:00",
                "from_account": v["account"],
                "from_name": v["name"],
                "to_account": collection_acc,
                "to_name": collection_holder,
                "amount_paise": amount,
                "reference": f"UPI/{self.rng.randint(100000000000, 999999999999)}/{collection_holder[:8]}@okhdfc"
            })

        # Collection -> Mules
        for j, m in enumerate(mules):
            txn_date = base_date + timedelta(days=4)
            amount = total_inflow_paise // len(mules)
            data["transactions"].append({
                "txn_id": f"TXN-MUL-R{ring_id}-{j+1:03d}",
                "date": txn_date.strftime("%Y-%m-%d"),
                "time": "14:15:00",
                "from_account": collection_acc,
                "from_name": collection_holder,
                "to_account": m["account"],
                "to_name": m["name"],
                "amount_paise": amount,
                "reference": f"NEFT-N{self.rng.randint(100000, 999999)}-{m['name'].replace(' ', '')}-{m['account']}"
            })

        # Mules -> Organizer Account
        for k, m in enumerate(mules):
            txn_date = base_date + timedelta(days=5)
            amount = total_inflow_paise // len(mules) - 1000000 # small commission kept
            data["transactions"].append({
                "txn_id": f"TXN-ORG-R{ring_id}-{k+1:03d}",
                "date": txn_date.strftime("%Y-%m-%d"),
                "time": "16:45:00",
                "from_account": m["account"],
                "from_name": m["name"],
                "to_account": organizer_account,
                "to_name": organizer_name,
                "amount_paise": amount,
                "reference": f"IMPS/{self.rng.randint(10000000, 99999999)}/{organizer_name[:6]}/{organizer_account}"
            })

        # Organizer -> Shell Company
        shell_date = base_date + timedelta(days=6)
        shell_amount_paise = int(total_inflow_paise * 0.85)
        data["transactions"].append({
            "txn_id": f"TXN-SHELL-R{ring_id}-001",
            "date": shell_date.strftime("%Y-%m-%d"),
            "time": "18:00:00",
            "from_account": organizer_account,
            "from_name": organizer_name,
            "to_account": shell_acc,
            "to_name": shell_org,
            "amount_paise": shell_amount_paise,
            "reference": f"RTGS/R{self.rng.randint(100000, 999999)}/{shell_org[:8]}/{shell_acc}"
        })

        # Call network & Sudden Spike on Organizer's New SIM
        # Baseline: few calls per day for first 5 days
        for d in range(1, 6):
            day = base_date + timedelta(days=d)
            for _ in range(self.rng.randint(1, 3)):
                target_phone = self.generate_phone()
                data["calls"].append({
                    "call_id": f"CALL-BASE-R{ring_id}-{d}-{self.rng.randint(100,999)}",
                    "caller": organizer_phone,
                    "receiver": target_phone,
                    "date": day.strftime("%Y-%m-%d"),
                    "time": f"{self.rng.randint(9, 21):02d}:{self.rng.randint(10, 59):02d}:00",
                    "duration_seconds": self.rng.randint(45, 180),
                    "call_type": "out"
                })

        # Spike day (Day 6)
        spike_day = base_date + timedelta(days=6)
        planted["spike_onset_date"] = spike_day.strftime("%Y-%m-%d")
        planted["spike_peak_date"] = spike_day.strftime("%Y-%m-%d")
        planted["spike_peak_calls"] = 35 * mult

        for call_idx in range(planted["spike_peak_calls"]):
            target = recruiter_phone if call_idx % 2 == 0 else mules[0]["phone"]
            data["calls"].append({
                "call_id": f"CALL-SPK-R{ring_id}-{call_idx+1:03d}",
                "caller": organizer_phone,
                "receiver": target,
                "date": spike_day.strftime("%Y-%m-%d"),
                "time": f"{self.rng.randint(10, 22):02d}:{self.rng.randint(10, 59):02d}:00",
                "duration_seconds": self.rng.randint(60, 300),
                "call_type": "out"
            })

        # FIRs (Recruiter appears under name variants, Organizer appears in ZERO FIRs)
        if include_fir:
            r_surname = recruiter_name.split()[-1]
            r_first = recruiter_name.split()[0]
            name_variants = [
                recruiter_name,
                f"{r_first[0]}. {r_surname}",
                f"{r_first} Kumar {r_surname}"
            ]
            fir_stations = ["Cyber Police Station North", "Crime Branch Dwarka", "Central District Police"]
            for idx, (variant, station) in enumerate(zip(name_variants, fir_stations)):
                fir_date = base_date + timedelta(days=8 + idx)
                fir_id = f"FIR-2026-{100 * ring_id + 1 + idx:03d}"
                data["firs"].append({
                    "fir_id": fir_id,
                    "police_station": station,
                    "date": fir_date.strftime("%Y-%m-%d"),
                    "text": (
                        f"FIRST INFORMATION REPORT\n"
                        f"FIR ID: {fir_id}\n"
                        f"Police Station: {station}\n"
                        f"Date of Report: {fir_date.strftime('%Y-%m-%d')}\n\n"
                        f"The complainant reported unauthorized fund debits after receiving online investment calls.\n"
                        f"Primary contact number of the representative was noted as {recruiter_phone}.\n"
                        f"The representative was identified as {variant} operating vehicle registration {recruiter_veh}.\n"
                        f"Funds were routed to bank a/c {collection_acc}.\n"
                        f"Statutory enquiry under section 63 BSA initiated.\n"
                    )
                })

    def _build_sparse_tiny(self, data: dict, planted: dict, base_date: datetime):
        # 10 to 40 rows total, 1-2 FIRs
        v_name = f"{self.fake.first_name()} {self.fake.last_name()}"
        v_acc = self.generate_account()
        m_name = f"{self.fake.first_name()} {self.fake.last_name()}"
        m_acc = self.generate_account()
        m_phone = self.generate_phone()

        # 8 transactions
        data["transactions"].append({
            "txn_id": "TXN-TINY-001",
            "date": (base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            "time": "10:00:00",
            "from_account": v_acc,
            "from_name": v_name,
            "to_account": m_acc,
            "to_name": m_name,
            "amount_paise": 2000000,
            "reference": f"UPI/TINY1/{m_name[:6]}"
        })

        # 12 calls
        for i in range(12):
            data["calls"].append({
                "call_id": f"CALL-TINY-{i+1:03d}",
                "caller": m_phone,
                "receiver": self.generate_phone(),
                "date": (base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                "time": f"1{i}:15:00",
                "duration_seconds": 45,
                "call_type": "out"
            })

        # 1 FIR
        data["firs"].append({
            "fir_id": "FIR-2026-901",
            "police_station": "Local Outpost Station",
            "date": (base_date + timedelta(days=3)).strftime("%Y-%m-%d"),
            "text": (
                "FIRST INFORMATION REPORT\n"
                "FIR ID: FIR-2026-901\n"
                "Police Station: Local Outpost Station\n"
                f"Complainant {v_name} noted debit to account {m_acc}.\n"
            )
        })

    # -----------------------------------------------------------------
    # FORMAT EXPORTERS
    # -----------------------------------------------------------------

    def write_clean_format(self, data: dict, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        # 1. cdr.csv and cdr.json
        if data["calls"]:
            pd.DataFrame(data["calls"]).to_csv(out_dir / "cdr.csv", index=False)
            with open(out_dir / "cdr.json", "w", encoding="utf-8") as f:
                json.dump(data["calls"], f, indent=2)

        # 2. bank_transactions.csv and bank_transactions.json
        if data["transactions"]:
            bank_df = pd.DataFrame(data["transactions"])
            bank_df["amount"] = bank_df["amount_paise"] / 100.0
            bank_df.to_csv(out_dir / "bank_transactions.csv", index=False)
            with open(out_dir / "bank_transactions.json", "w", encoding="utf-8") as f:
                json.dump(data["transactions"], f, indent=2)

        # 3. sdr.csv
        if data["sdr"]:
            pd.DataFrame(data["sdr"]).to_csv(out_dir / "sdr.csv", index=False)

        # 4. account_master.csv
        if data["account_master"]:
            pd.DataFrame(data["account_master"]).to_csv(out_dir / "account_master.csv", index=False)

        # 5. ip_logs.csv
        if data["ip_logs"]:
            pd.DataFrame(data["ip_logs"]).to_csv(out_dir / "ip_logs.csv", index=False)

        # 6. FIR text files
        for fir in data["firs"]:
            with open(out_dir / f"{fir['fir_id']}.txt", "w", encoding="utf-8") as f:
                f.write(fir["text"])

    def write_messy_format(self, data: dict, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        # 1. Messy Excel CDR (if calls exist)
        if data["calls"]:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Call_Records_Extracted"
            ws.append(["DEPARTMENT OF TELECOMMUNICATIONS - LAW ENFORCEMENT REPORT"])
            ws.append(["CONFIDENTIAL - FOR INVESTIGATIVE USE ONLY"])
            ws.append(["Generated Timestamp: 2026-08-15 | Case Reference: CC-101"])
            ws.append(["A-Party", "B-Party", "Call Date", "Call Time", "Dur(sec)", "Call Type"])

            for c in data["calls"]:
                d_obj = datetime.strptime(c["date"], "%Y-%m-%d")
                d_str = d_obj.strftime("%d/%m/%Y")
                a_party = f"+91 {c['caller'][:5]} {c['caller'][5:]}"
                b_party = f"0{c['receiver']}"
                ws.append([a_party, b_party, d_str, c["time"], c["duration_seconds"], "MOC" if c["call_type"] == "out" else "MTC"])

            # Sheet 2: Tower metadata
            ws2 = wb.create_sheet(title="Tower_Metadata")
            ws2.append(["Cell ID", "Azimuth", "Tower Location"])
            ws2.append(["CGI-404-10-1234", "120", "Connaught Place Hub"])
            wb.save(out_dir / "cdr_messy.xlsx")

        # 2. Messy Bank CSV (with banner rows and comma amounts like 5,00,000.00, cp1252 encoding)
        if data["transactions"]:
            with open(out_dir / "bank_messy.csv", "w", encoding="cp1252", errors="ignore") as f:
                f.write("CENTRAL BANK STATEMENT EXPORT\n")
                f.write("Account Filter: All Connected Transactions\n")
                f.write("Txn Date,Value Date,Remitter A/c,Beneficiary A/c,Amount (INR),Reference\n")
                for t in data["transactions"]:
                    amt_inr = t["amount_paise"] / 100.0
                    amt_str = f'"{amt_inr:,.2f}"'
                    f.write(f"{t['date']},{t['date']},{t['from_account']},{t['to_account']},{amt_str},{t['reference']}\n")
                f.write(f"TOTAL,,,,\"{data['ground_truth']['total_volume_inr']:,.2f}\",\n")

        # Copy FIRs
        for fir in data["firs"]:
            with open(out_dir / f"{fir['fir_id']}.txt", "w", encoding="utf-8") as f:
                f.write(fir["text"])

    def write_statement_format(self, data: dict, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        # Write individual single-account statements
        txns_by_acct = {}
        for t in data["transactions"]:
            fa = t["from_account"]
            ta = t["to_account"]
            txns_by_acct.setdefault(fa, []).append((t, "debit"))
            txns_by_acct.setdefault(ta, []).append((t, "credit"))

        for acct, txns in list(txns_by_acct.items())[:10]:
            with open(out_dir / f"statement_{acct}.csv", "w", encoding="utf-8") as f:
                f.write(f"Account No: {acct}\n")
                f.write("Account Holder: Primary Account Customer\n")
                f.write("Date,Narration,Withdrawal/Debit,Deposit/Credit,Balance\n")
                balance = 1000000.0
                for t, mode in txns:
                    amt = t["amount_paise"] / 100.0
                    dr = f"{amt:.2f}" if mode == "debit" else ""
                    cr = f"{amt:.2f}" if mode == "credit" else ""
                    balance = balance - amt if mode == "debit" else balance + amt
                    f.write(f"{t['date']},{t['reference']},{dr},{cr},{balance:.2f}\n")

        # Write calls and FIRs if present
        if data["calls"]:
            pd.DataFrame(data["calls"]).to_csv(out_dir / "cdr.csv", index=False)
        for fir in data["firs"]:
            with open(out_dir / f"{fir['fir_id']}.txt", "w", encoding="utf-8") as f:
                f.write(fir["text"])

    def write_paysim_format(self, data: dict, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        # PaySim columns: step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud
        rows = []
        for idx, t in enumerate(data["transactions"]):
            rows.append({
                "step": idx * 2 + 1,
                "type": "TRANSFER",
                "amount": t["amount_paise"] / 100.0,
                "nameOrig": f"C{t['from_account']}",
                "oldbalanceOrg": 500000.0,
                "newbalanceOrg": 500000.0 - (t["amount_paise"] / 100.0),
                "nameDest": f"M{t['to_account']}",
                "oldbalanceDest": 10000.0,
                "newbalanceDest": 10000.0 + (t["amount_paise"] / 100.0),
                "isFraud": 1 if "SHELL" in t.get("txn_id", "") or "ORG" in t.get("txn_id", "") else 0
            })
        if rows:
            pd.DataFrame(rows).to_csv(out_dir / "paysim_transactions.csv", index=False)

        # Write calls and FIRs if present
        if data["calls"]:
            pd.DataFrame(data["calls"]).to_csv(out_dir / "cdr.csv", index=False)
        for fir in data["firs"]:
            with open(out_dir / f"{fir['fir_id']}.txt", "w", encoding="utf-8") as f:
                f.write(fir["text"])

    def generate(self, scenario: str, format_type: str, size: str, out_dir: str):
        data = self.build_scenario_data(scenario, size)
        out_path = Path(out_dir)

        if format_type == "clean":
            self.write_clean_format(data, out_path)
        elif format_type == "messy":
            self.write_messy_format(data, out_path)
        elif format_type == "statement":
            self.write_statement_format(data, out_path)
        elif format_type == "paysim":
            self.write_paysim_format(data, out_path)

        # Write ground_truth.json (ALWAYS created, test-only ground truth)
        with open(out_path / "ground_truth.json", "w", encoding="utf-8") as f:
            json.dump(data["ground_truth"], f, indent=2)

        print(f"[OK] Generated {scenario} ({format_type}, {size}, seed={self.seed}) in {out_path.resolve()}")
        return True

def main():
    parser = argparse.ArgumentParser(description="Deterministic synthetic data generator for Case Connect AI")
    parser.add_argument("--scenario", default="ring", choices=["ring", "benign_heavy", "cdr_only", "bank_only", "chain", "hub_spoke", "two_rings", "sparse_tiny", "random_mix"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--format", default="clean", choices=["clean", "messy", "statement", "paysim"])
    parser.add_argument("--size", default="small", choices=["small", "medium", "large"])
    parser.add_argument("--out", default="data/synthetic/sample")
    args = parser.parse_args()

    gen = SyntheticDataGenerator(seed=args.seed)
    gen.generate(args.scenario, args.format, args.size, args.out)

if __name__ == "__main__":
    main()
