from thermal.exposure import doses as dose
from thermal.decision import classify as disposition
from thermal.decision import windows as rate_windows
from thermal.gap_register import register as gap_register
from thermal.calibration_review import review as calibration_review
from thermal.interval_accounts import account as interval_accounts
from thermal.checkpoints import inspect as checkpoints
from thermal.cold_spot import measure as cold_spot
from thermal.cold_windows import report as cold_windows
from thermal.clock_alignment import align as clock_alignment

PRODUCT = '0016-thermal-indicator-dose'
TITLE = '包装温度剂量工作台'
WORK_LABEL = '温度试验 / 观测与断档'
THEME = 'thermal'
DEFAULT_DATASET = 'thermal-batch'
PORT = 8816

OPERATIONS = {
    'dose': ('剂量积分', dose),
    'disposition': ('剂量判定', disposition),
    'rate-windows': ('速率时段', rate_windows),
    'gap-register': ('断档清单', gap_register),
    'calibration-review': ('平行校准复核', calibration_review),
    'interval-accounts': ('分段剂量账', interval_accounts),
    'checkpoints': ('累计剂量检查点', checkpoints),
    'cold-spot': ('双位置冷点剂量', cold_spot),
    'cold-windows': ('冷点分窗凭据', cold_windows),
    'clock-alignment': ('双钟对时与剂量', clock_alignment),
}
def _review_eligible(report):
    return report['checkpoints'][-1]['state'] == 'reached'


REVIEW = ('checkpoints', _review_eligible)
REQUIRED = ('dose', 'disposition', 'rate-windows')
