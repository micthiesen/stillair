# Testing

[`test-matrix.csv`](test-matrix.csv) is the commissioning matrix: every release test with its
method, acceptance limit, and blank Result/Owner/Date sign-off fields. Fill in results as
tests are run; limits are the minimum release basis and can be tightened once measured data
exists. Context for the phases lives in [../docs/build.md](../docs/build.md).

Prefixes: `PCB-` board bring-up, `TACH-` independent overspeed, `DRV-` motor drive, `CTL-`
supervisor/control, `MEC-` mechanical/rotor, `INS-` installation.
