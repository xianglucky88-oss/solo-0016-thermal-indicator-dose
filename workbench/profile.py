from thermal.exposure import doses as dose
from thermal.decision import classify as disposition
from thermal.decision import windows as rate_windows
from thermal.gap_register import register as gap_register
from thermal.calibration_review import review as calibration_review
from thermal.interval_accounts import account as interval_accounts

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
}
REQUIRED = ('dose', 'disposition', 'rate-windows')
