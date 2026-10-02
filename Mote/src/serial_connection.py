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

    def save(self) -> str:
        """Sauvegarde la configuration mac courante en mémoire non volatile."""

        return self.send_command("mac save")

    def close(self) -> None:
        """Ferme le port série."""

        self._serial.close()
