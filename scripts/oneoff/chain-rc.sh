#!/bin/sh
# RC gate chain (2 Oct): deploy v7.1-rc, validate RinghatchetsReady + CTRL in full, then the section-7 RC rerun list.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
export SW_TOOL=/Users/nathanielcannon/Claude/Projects/sw-wt/rc
L=data/logs/chain-rc.log
echo "=== chain-rc start $(date +%H:%M) rc=$(git -C $SW_TOOL log -1 --format=%h)" >> $L
scripts/cx-lifecycle.sh title >> $L 2>&1
scripts/cx-lifecycle.sh deploy >> $L 2>&1
scripts/cx-lifecycle.sh deploy-tool $SW_TOOL/scripts >> $L 2>&1 || { echo "=== chain-rc deploy FAILED" >> $L; exit 1; }
.venv/bin/python scripts/validate-full.py --fort RinghatchetsReady > data/logs/validate-rc-rh.log 2>&1
echo "=== validate RH exit $? $(tail -3 data/logs/validate-rc-rh.log | tr '\n' ' ')" >> $L
.venv/bin/python scripts/validate-full.py > data/logs/validate-rc-ctrl.log 2>&1
echo "=== validate CTRL exit $? $(tail -3 data/logs/validate-rc-ctrl.log | tr '\n' ' ')" >> $L
SEC7_CIV_SEASONS=0 .venv/bin/python scripts/alpha4-sec7.py --only DEPLOY,FACTS,PANEL,S7_STP1,S7_FSH3,S7_FSH4,S7_GRD1,S7_EXU1,S7_VF1,S7_IRRM,S7_IRRP2,S7_IRRR35,S7_TRIM,S7_NAT > data/logs/sec7-rc.log 2>&1
echo "=== sec7 exit $?" >> data/logs/sec7-rc.log
echo "=== chain-rc done $(date +%H:%M)" >> $L
