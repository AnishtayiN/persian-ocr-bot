from handlers.start import router as start_router
from handlers.ocr import router as ocr_router
from handlers.instagram import router as ig_router
from handlers.referral import router as ref_router
from handlers.admin import router as admin_router

__all__ = ["start_router", "ocr_router", "ig_router", "ref_router", "admin_router"]
