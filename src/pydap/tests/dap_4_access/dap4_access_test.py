#
# Test loading a URL from the EarthData Cloud (EDC) OPeNDAP server using the
# new (8/18/22) PyDAP DAP4 support. This dataset will not load using DAP2.
#

import configparser
import logging
import time

import requests

import pydap.client

logging.basicConfig(
    filename="dap4_access_test.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s : %(message)s",
)

logger = logging.getLogger(__name__)


class SessionEarthData(requests.Session):
    AUTH_HOST = "urs.earthdata.nasa.gov"

    def __init__(self, username, password):
        super().__init__()
        self.auth = (username, password)

    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        url = prepared_request.url
        if "Authorization" in headers:
            original_parsed = requests.utils.urlparse(response.request.url)
            redirect_parsed = requests.utils.urlparse(url)
            if (
                (original_parsed.hostname != redirect_parsed.hostname)
                and redirect_parsed.hostname != self.AUTH_HOST
                and original_parsed.hostname != self.AUTH_HOST
            ):
                del headers["Authorization"]
        return


def main():
    config = configparser.ConfigParser()
    config.read("user.config")
    username = config["user"]["user"]
    password = config["user"]["pwd"]
    session = SessionEarthData(username=username, password=password)

    dap4_schema = "dap4"

    host = "opendap.earthdata.nasa.gov"
    path = "/collections/C1996881146-POCLOUD/granules/"
    dataset = "20220531090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1"

    dap4_url = f"{dap4_schema}://{host}{path}{dataset}"

    # open the dap4 URL
    print(f"Open this URL: {dap4_url}")
    i = 0
    while True:
        start = time.time()
        pydap_ds = pydap.client.open_url(dap4_url, session=session)

        print("The attributes:")
        print(pydap_ds["sea_ice_fraction"].attributes)
        i += 1
        print(f"Call {i}")
        variable = pydap_ds["sea_ice_fraction"][0, 1700:1799:10, 1800:1900:10]
        print(f"Time for request: {time.time() - start}")
        print('A subset of the "sea_ice_fraction" variable')
        print(variable.data)


if __name__ == "__main__":
    main()
