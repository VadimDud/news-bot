"""Доверие к российским корневым CA для T-Bank Invest API (gRPC).

T-Bank выдаёт сертификат CN=*.tinkoff.ru, подписанный российским «Russian
Trusted Sub CA» (Минцифры), которого нет в стандартном trust store OpenSSL.
Поэтому TLS-handshake падает с ``CERTIFICATE_VERIFY_FAILED: self signed
certificate in certificate chain``. Решение: подмешивать бандл российских
корневых сертификатов в gRPC-канал через ``root_certificates``.

Бандл скачивается с gu-st.ru и кэшируется в ``DATA_DIR/tinkoff_ru_ca.pem``
(volume переживает перезапуски). Патч применяется один раз на процесс.
"""

import logging
import urllib.request
from pathlib import Path

from . import config

logger = logging.getLogger("moex_trader.tinkoff_ssl")

RU_CA_URLS = (
    "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt",
    "https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt",
)

CACHE_FILENAME = "tinkoff_ru_ca.pem"

_patch_installed = False


def _download_bundle(path: Path) -> bytes:
    parts = []
    for url in RU_CA_URLS:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            parts.append(resp.read())
    data = b"\n".join(parts)
    path.write_bytes(data)
    return data


def _fetch_bundle(path: Path) -> bytes:
    if path.exists() and path.stat().st_size > 0:
        logger.info("Использую кэш российских CA: %s", path)
        return path.read_bytes()
    logger.info("Скачиваю российские корневые CA с gu-st.ru")
    return _download_bundle(path)


def _patch_create_channel(bundle: bytes) -> None:
    import grpc

    import tinkoff.invest.channels as channels
    import tinkoff.invest.clients as clients

    def create_channel(*, target=None, options=None, force_async=False,
                       compression=None, interceptors=None):
        target = target or channels.INVEST_GRPC_API
        if options is None:
            options = []
        options = channels._with_max_receive_message_length_option(options)
        creds = grpc.ssl_channel_credentials(root_certificates=bundle)
        if force_async:
            return grpc.aio.secure_channel(
                target, creds, options, compression, interceptors
            )
        return grpc.secure_channel(target, creds, options, compression)

    channels.create_channel = create_channel
    clients.create_channel = create_channel


def install_ru_ca() -> bool:
    """Применить доверие к российским CA (идемпотентно).

    Возвращает True, если патч активен или не требуется. При невозможности
    скачать бандл без кэша — лог-warning и стандартная проверка (False).
    """
    global _patch_installed
    if _patch_installed:
        return True
    if not config.TINKOFF_SSL_RU_CA:
        return False
    try:
        bundle = _fetch_bundle(Path(config.DATA_DIR) / CACHE_FILENAME)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Не удалось получить российские CA (%s); использую стандартную проверку", exc
        )
        return False
    _patch_create_channel(bundle)
    _patch_installed = True
    logger.info("Установлено доверие к российским корневым CA для T-Bank API")
    return True