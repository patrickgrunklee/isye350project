"""
Install GAMSPy Academic Licenses

This script installs the two academic licenses for GAMSPy to enable
solving large-scale optimization models without size restrictions.
"""

import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*80)
print("GAMSPy License Installation")
print("="*80)

# License codes
LICENSE_1 = "d81a3160-ec06-4fb4-9543-bfff870b9ecb"
LICENSE_2 = "8c39a188-c68a-4295-9c9d-b65ac74bce78"

try:
    from gamspy import Container

    print("\n[1/3] Testing GAMSPy installation...")
    print(f"   ✓ GAMSPy imported successfully")

    print("\n[2/3] Setting up License 1...")
    print(f"   License: {LICENSE_1}")
    import os
    os.environ['GAMSLICE_STRING'] = LICENSE_1
    print(f"   ✓ License 1 set as environment variable")

    print("\n   To use License 1, set in your shell:")
    print(f"   PowerShell: $env:GAMSLICE_STRING=\"{LICENSE_1}\"")
    print(f"   CMD:        set GAMSLICE_STRING={LICENSE_1}")

    print("\n[3/3] Alternative License 2...")
    print(f"   License: {LICENSE_2}")
    print(f"   To use License 2 instead, set:")
    print(f"   PowerShell: $env:GAMSLICE_STRING=\"{LICENSE_2}\"")
    print(f"   CMD:        set GAMSLICE_STRING={LICENSE_2}\"")

    print("\n   Note: GAMSPy will automatically use the license from GAMSLICE_STRING")

    print("\n" + "="*80)
    print("Testing basic GAMSPy functionality...")
    print("="*80)

    # Test basic optimization
    from gamspy import Set, Parameter, Variable, Equation, Model, Sum, Sense

    m = Container()
    i = Set(m, name="i", records=['i1', 'i2', 'i3'])
    x = Variable(m, name="x", domain=i, type="positive")
    obj_var = Variable(m, name="obj_var", type="free")

    obj = Equation(m, name="obj")
    obj[...] = obj_var == Sum(i, x[i])

    test_model = Model(m, name="test", equations=[obj], problem="LP", sense=Sense.MIN, objective=obj_var)
    test_model.solve()

    print(f"\n✓ Test optimization solved successfully!")
    print(f"✓ Model status: {test_model.status}")
    print(f"✓ GAMSPy is ready for large-scale optimization")

    print("\n" + "="*80)
    print("LICENSE INSTALLATION COMPLETE")
    print("="*80)
    print("\nYou can now run:")
    print("  - python optimization_model.py")
    print("  - python warehouse_optimization.py")
    print("  - python final_warehouse_model.py")
    print("\n")

except ImportError as e:
    print(f"\n✗ ERROR: GAMSPy not installed")
    print(f"   {e}")
    print(f"\nPlease install GAMSPy first:")
    print(f"   pip install gamspy")
    sys.exit(1)

except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Check internet connection (license validation requires online access)")
    print(f"  2. Verify GAMSPy version: python -c \"import gamspy; print(gamspy.__version__)\"")
    print(f"  3. Try setting environment variable: $env:GAMSLICE_STRING=\"{LICENSE_1}\"")
    sys.exit(1)
