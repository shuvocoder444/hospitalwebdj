from .models import HospitalSetting

def hospital_settings(request):
    """
    Context processor to inject HospitalSetting singleton into all templates.
    """
    try:
        setting = HospitalSetting.get_settings()
    except Exception:
        setting = None
    return {'hospital_setting': setting}
