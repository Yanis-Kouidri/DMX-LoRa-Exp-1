from serial import Serial


class RN2483Connection:
    """Gestion de la connexion série avec le RN2483."""

    def __init__(
        self,
        port: str,
        baudrate: int = 57600,
        timeout: float = 1.0,
    ) -> None:
        self._serial = Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
        )

    def send_command(self, command: str) -> str:
        """Envoie une commande AT et retourne la réponse (une seule ligne)."""

        self._serial.reset_input_buffer()

        self._serial.write(f"{command}\r\n".encode())

        response = self._serial.readline()

        return response.decode(errors="replace").strip()

    def write_command(self, command: str) -> None:
        """Envoie une commande sans attendre de réponse (lecture gérée par l'appelant)."""

        self._serial.write(f"{command}\r\n".encode())

    def read_available(self) -> bytes:
        """Lit les octets disponibles, en attendant au plus le timeout du port."""

        return self._serial.read(self._serial.in_waiting or 1)

    def resync_baudrate(self) -> None:
        """
        Relance l'auto-baud du RN2483 : condition Break suivie de 0x55.

        Procédure documentée (guide DS40001784G, sys sleep / UART interface)
        pour recaler le débit du module sur celui de l'hôte. Sans effet sur
        la configuration ; inoffensif aussi si le module est en bootloader.
        """

        self._serial.send_break(duration=0.05)
        self._serial.write(b"\x55")
        self._serial.flush()

    def _read_line(self, timeout: float) -> str:
        """Lit une ligne avec un timeout dédié, sans altérer le timeout par défaut du port."""

        original_timeout = self._serial.timeout
        self._serial.timeout = timeout
        try:
            line = self._serial.readline()
        finally:
            self._serial.timeout = original_timeout

        return line.decode(errors="replace").strip()

    def send_mac_tx(
        self,
        payload: str,
        confirmed: bool = False,
        async_timeout: float = 5.0,
    ) -> tuple[str, str]:
        """
        Envoie une trame LoRaWAN (mac tx) et lit les DEUX réponses du module RN2483 :

        1. La réponse immédiate à la commande : "ok" si acceptée par le module,
           ou une erreur (ex: "invalid_data_len", "not_joined", "no_free_ch"
           si le duty cycle bloque l'émission sur le canal).
        2. La réponse asynchrone envoyée après la transmission effective sur
           l'antenne (et l'attente des fenêtres RX1/RX2) : "mac_tx_ok" en
           uncnf, "mac_rx <port> <data>" ou "mac_err" en cnf si pas d'ACK reçu.

        Si `immediate` n'est pas "ok", la commande a été rejetée avant toute
        émission radio : `async_response` sera une chaîne vide dans ce cas.

        Le délai `async_timeout` doit être suffisant pour couvrir l'attente
        RX1 + RX2 (quelques centaines de ms à ~2s selon le paramétrage),
        d'où la valeur par défaut de 5s en marge de sécurité.
        """

        mode = "cnf" if confirmed else "uncnf"
        self._serial.reset_input_buffer()
        self._serial.write(f"mac tx {mode} 1 {payload}\r\n".encode())

        immediate = self._read_line(timeout=1.0)

        if immediate.lower() != "ok":
            return immediate, ""

        async_response = self._read_line(timeout=async_timeout)
        return immediate, async_response

    def set_adr(self, enabled: bool) -> str:
        """Active/désactive l'Adaptive Data Rate (à désactiver pour un test SF manuel)."""

        return self.send_command(f"mac set adr {'on' if enabled else 'off'}")

    def set_dr(self, dr: int) -> str:
        """
        Fixe le Data Rate LoRaWAN (pilote le SF utilisé).

        Correspondance EU868 (BW 125 kHz) :
            DR0 = SF12   DR1 = SF11   DR2 = SF10
            DR3 = SF9    DR4 = SF8    DR5 = SF7
        """

        if not 0 <= dr <= 5:
            raise ValueError("DR doit être compris entre 0 et 5 (EU868)")

        return self.send_command(f"mac set dr {dr}")

    def is_joined(self) -> bool:
        """
        Indique si le module a déjà rejoint le réseau.

        `mac get status` renvoie un champ de bits en hexadécimal (firmware
        1.0.5+) : bits 3:0 = état MAC, bit 4 = statut de join.
        """

        status = self.send_command("mac get status")
        try:
            return bool(int(status, 16) & 0x10)
        except ValueError:
            raise RuntimeError(f"Réponse inattendue à 'mac get status' : {status!r}")

    def join_otaa(self, async_timeout: float = 20.0) -> tuple[str, str]:
        """
        Lance un join OTAA et lit les DEUX réponses du module :

        1. La réponse immédiate : "ok" si la procédure démarre, sinon une
           erreur ("keys_not_init", "no_free_ch", "silent", "busy"...).
        2. La réponse asynchrone : "accepted" ou "denied".

        Si `immediate` n'est pas "ok", `async_response` est une chaîne vide.
        """

        self._serial.reset_input_buffer()
        self._serial.write(b"mac join otaa\r\n")

        immediate = self._read_line(timeout=1.0)

        if immediate.lower() != "ok":
            return immediate, ""

        async_response = self._read_line(timeout=async_timeout)
        return immediate, async_response

    def set_channel_duty_cycle(self, channel: int, dcycle: int) -> str:
        """
        Règle le duty cycle d'un canal : duty cycle (%) = 100 / (dcycle + 1).

        `dcycle = 0` correspond à 100 %, ce qui lève la limitation imposée
        par le module (réservé aux tests en environnement fermé).
        """

        return self.send_command(f"mac set ch dcycle {channel} {dcycle}")

    def get_dr(self) -> int:
        """Retourne le Data Rate actuellement utilisé par le module."""

        response = self.send_command("mac get dr")
        try:
            return int(response)
        except ValueError:
            raise RuntimeError(f"Réponse inattendue à 'mac get dr' : {response!r}")

    def save(self) -> str:
        """Sauvegarde la configuration mac courante en mémoire non volatile."""

        return self.send_command("mac save")

    def close(self) -> None:
        """Ferme le port série."""

        self._serial.close()
