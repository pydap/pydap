import codecs
import pickle


def main():
    logfile = "dap4_access_test.log"

    with open(logfile, "r") as f:
        f = f.read()

    p = f.split("----BEGIN PICKLE-----")[1].split("----END PICKLE-----")[0]
    p = "".join(p).strip().replace("\n", "")

    response = pickle.loads(codecs.decode(p.encode("utf-8"), "base64"))

    print(dict(response.headers))
    with open("out.html", "w") as f:
        f.write(response.text)

    with open("response.pickle", "wb") as f:
        pickle.dump(response, f)


if __name__ == "__main__":
    main()
