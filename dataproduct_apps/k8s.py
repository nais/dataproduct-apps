import os


def init_k8s_client():
    # TODO: Implement loading from KUBECONFIG for local development
    from k8s import config
    token_file = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if os.path.exists(token_file):
        with open(token_file) as fobj:
            config.api_token = fobj.read().strip()
    config.verify_ssl = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    config.api_server = "https://kubernetes.default"