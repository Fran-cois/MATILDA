import os
import re
import glob
import logging
from datetime import datetime
from tempfile import TemporaryDirectory

from algorithms.rule_discovery_algorithm import RuleDiscoveryAlgorithm
from utils.rules import Predicate, TGDRule
from utils.run_cmd import run_cmd


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnyBURL(RuleDiscoveryAlgorithm):
    """
    AnyBURL integration to discover rules from a TSV knowledge graph.

    Expected binaries:
    - A jar available in src/algorithms/bins/anyburl/*.jar
      or provide env var ANYBURL_JAR with an absolute path to the jar.
    """

    def discover_rules(self, **kwargs) -> list:
        algorithm_name = "anyburl"
        results_path = kwargs.get("results_dir", "results")
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Input graph (TSV) provided by the database wrapper
        database_path = self.database.database_path_tsv
        # If a directory is provided, pick the first .tsv file inside
        training_path = database_path
        if os.path.isdir(database_path):
            tsvs = sorted(glob.glob(os.path.join(database_path, "*.tsv")))
            if tsvs:
                training_path = tsvs[0]

        # Resolve jar path
        jar_path = os.environ.get("ANYBURL_JAR")
        if not jar_path:
            jar_candidates = glob.glob(os.path.join(script_dir, "bins", "anyburl", "*.jar"))
            jar_path = jar_candidates[0] if jar_candidates else None

        if not jar_path or not os.path.exists(jar_path):
            logger.warning(
                "AnyBURL jar introuvable. Placez le jar dans src/algorithms/bins/anyburl/ ou définissez ANYBURL_JAR."
            )
            return []

        # Prepare output directory for AnyBURL artifacts
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_output_dir = os.path.join(results_path, f"{timestamp}_{algorithm_name}")
        os.makedirs(run_output_dir, exist_ok=True)

        # Build a minimal settings file
        settings_content = (
            f"PATH_TRAINING = {training_path}\n"
            f"WORKER_THREADS = 4\n"
            f"PATH_OUTPUT = {run_output_dir}/\n"
            f"SNAPSHOTS_AT = 100\n"  # Generate snapshot every 100 seconds
        )

        with TemporaryDirectory() as tmpdir:
            # Prepare settings for Docker (using container paths)
            training_basename = os.path.basename(training_path)
            docker_training_path = f"/data/{training_basename}"
            docker_output_path = "/output"
            
            docker_settings_content = (
                f"PATH_TRAINING = {docker_training_path}\n"
                f"WORKER_THREADS = 4\n"
                f"PATH_OUTPUT = {docker_output_path}/\n"
                f"SNAPSHOTS_AT = 100\n"  # Generate snapshot every 100 seconds
            )
            
            settings_path = os.path.join(tmpdir, "settings.properties")
            with open(settings_path, "w") as f:
                f.write(docker_settings_content)

            # Get absolute paths for Docker volumes
            training_dir = os.path.dirname(os.path.abspath(training_path))
            abs_output_dir = os.path.abspath(run_output_dir)
            abs_settings = os.path.abspath(settings_path)
            
            # Try Docker first (recommended), then fallback to direct Java
            docker_cmd = (
                f"docker run --rm "
                f"-v {training_dir}:/data:ro "
                f"-v {abs_output_dir}:/output:rw "
                f"-v {abs_settings}:/app/settings.properties:ro "
                f"anyburl:java11 /app/settings.properties"
            )
            
            ok = run_cmd(docker_cmd, timeout=600)
            
            if not ok:
                logger.warning("Docker execution failed, trying direct Java...")
                # Fallback to direct Java with original settings
                settings_path_java = os.path.join(tmpdir, "settings_java.properties")
                with open(settings_path_java, "w") as f:
                    f.write(settings_content)
                
                candidates = []
                candidates.append(f"java -Xmx15G -jar {jar_path} {settings_path_java}")
                main_candidates = [
                    os.environ.get("ANYBURL_MAIN", "de.unima.ki.anyburl.Launch"),
                    "de.unima.ki.anyburl.Learn",
                    "de.unima.ki.anyburl.Apply",
                    "de.unima.ki.anyburl.Eval",
                ]
                for mc in main_candidates:
                    candidates.append(f"java -Xmx15G -cp {jar_path} {mc} {settings_path_java}")

                for cmd in candidates:
                    if run_cmd(cmd, timeout=600):
                        ok = True
                        break
                
                if not ok:
                    logger.error("Échec de l'exécution AnyBURL (Docker et Java natif).")
                    return []

        # Find produced rules file(s)
        # ANYBURL creates files like: PATH_OUTPUT-100, PATH_OUTPUT-200, etc.
        rule_files = (
            glob.glob(os.path.join(run_output_dir, "*-[0-9]*"))
            + glob.glob(os.path.join(run_output_dir, "*.rules"))
            + glob.glob(os.path.join(run_output_dir, "*rules.txt"))
            + glob.glob(os.path.join(run_output_dir, "*.txt"))
        )
        
        # Filter out log files
        rule_files = [f for f in rule_files if not f.endswith('_log')]

        if not rule_files:
            logger.warning("Aucun fichier de règles produit par AnyBURL.")
            return []

        # Prefer newest snapshot file (highest number)
        snapshot_files = [f for f in rule_files if re.search(r'-\d+$', f)]
        if snapshot_files:
            # Sort by snapshot number (extract number at end)
            snapshot_files.sort(key=lambda x: int(re.search(r'-(\d+)$', x).group(1)))
            rule_file = snapshot_files[-1]  # Take the latest snapshot
        else:
            # Fallback to .rules file or first file
            rule_file = next((p for p in rule_files if p.endswith('.rules')), rule_files[0])

        with open(rule_file, "r") as fh:
            raw_rules = fh.read()

        rules = self.parse_anyburl_rules(raw_rules)
        return rules

    @staticmethod
    def _parse_predicate_token(token: str) -> Predicate | None:
        """
        Parse a single token like relation(X,Y) or relation(X,"value") into a Predicate.
        """
        # Updated regex to handle quoted strings and dots in values
        m = re.match(r'\s*([A-Za-z0-9_:/.-]+)\s*\(\s*([^,\)]+)\s*,\s*([^\)]+)\s*\)\s*', token)
        if not m:
            return None
        rel, v1, v2 = m.group(1), m.group(2).strip(), m.group(3).strip()
        return Predicate(variable1=v1, relation=rel, variable2=v2)

    def _parse_literals(self, part: str) -> list:
        """Parse comma-separated literals or single literal, respecting parentheses"""
        literals = []
        # Split by comma only if not inside parentheses
        depth = 0
        current = []
        tokens = []
        for char in part:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                tokens.append(''.join(current).strip())
                current = []
                continue
            current.append(char)
        if current:
            tokens.append(''.join(current).strip())
        
        for tok in tokens:
            p = self._parse_predicate_token(tok)
            if p:
                literals.append(p)
        return literals

    def parse_anyburl_rules(self, rules_str: str) -> list:
        """
        Parse AnyBURL textual rules. Format is typically:
          support \t correct_predictions \t confidence \t rule
        Example: 345     40      0.11594202898550725     drinks.arg2(X,"6.000") <= drinks.arg1(X,A)
        
        Also tries to support formats:
          head <= body1 , body2  (meta ...)
          body1 , body2 => head  (meta ...)
        """
        rules: list[TGDRule] = []

        # Updated regex to not stop at parentheses
        pat_le = re.compile(r"^(.+?)\s*<=\s*(.+?)$")
        pat_ge = re.compile(r"^(.+?)\s*=>\s*(.+?)$")

        # Confidence/support capture (best-effort)
        pat_conf = re.compile(r"conf(?:idence)?\s*[:=]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
        pat_supp = re.compile(r"supp(?:ort)?\s*[:=]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)

        for line in rules_str.splitlines():
            s = line.strip()
            if not s or s.startswith('#'):
                continue

            # Try to parse tab-separated format first (ANYBURL default output)
            parts = s.split('\t')
            if len(parts) >= 4:
                try:
                    support = int(parts[0].strip())
                    correct_preds = int(parts[1].strip())
                    confidence = float(parts[2].strip())
                    rule_str = parts[3].strip()
                    
                    # Now parse the rule part
                    m = pat_le.match(rule_str)
                    if m:
                        head_part = m.group(1).strip()
                        body_part = m.group(2).strip()
                    else:
                        m = pat_ge.match(rule_str)
                        if m:
                            body_part = m.group(1).strip()
                            head_part = m.group(2).strip()
                        else:
                            m = None
                    
                    if m:
                        body_preds = self._parse_literals(body_part)
                        head_preds = self._parse_literals(head_part)
                        
                        if body_preds and head_preds:
                            display = f"{', '.join(map(str, body_preds))} => {', '.join(map(str, head_preds))}"
                            rules.append(
                                TGDRule(
                                    body=body_preds,
                                    head=head_preds,
                                    display=display,
                                    accuracy=-1.0,
                                    confidence=confidence,
                                )
                            )
                            continue
                except (ValueError, IndexError):
                    pass  # Fall through to regex parsing

            # Fallback: Try regex patterns for non-tabular format
            m = pat_le.match(s)
            if m:
                head_part = m.group(1).strip()
                body_part = m.group(2).strip()
            else:
                m = pat_ge.match(s)
                if m:
                    body_part = m.group(1).strip()
                    head_part = m.group(2).strip()
                else:
                    m = None

            if not m:
                continue

            body_preds = self._parse_literals(body_part)
            head_preds = self._parse_literals(head_part)

            if not body_preds or not head_preds:
                continue

            conf = -1.0
            sup = -1.0
            conf_m = pat_conf.search(s)
            sup_m = pat_supp.search(s)
            if conf_m:
                try:
                    conf = float(conf_m.group(1))
                except ValueError:
                    conf = -1.0
            if sup_m:
                try:
                    sup = float(sup_m.group(1))
                except ValueError:
                    sup = -1.0

            display = f"{', '.join(map(str, body_preds))} => {', '.join(map(str, head_preds))}"

            rules.append(
                TGDRule(
                    body=body_preds,
                    head=head_preds,
                    display=display,
                    accuracy=-1.0,
                    confidence=conf,
                )
            )

        return rules
