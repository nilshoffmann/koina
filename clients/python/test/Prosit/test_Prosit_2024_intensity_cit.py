from test.server_config import SERVER_GRPC, SERVER_HTTP
import tritonclient.grpc as grpcclient
import numpy as np
from pathlib import Path
import requests

# To ensure MODEL_NAME == test_<filename>.py
MODEL_NAME = Path(__file__).stem.replace("test_", "")


def test_available_http():
    req = requests.get(f"{SERVER_HTTP}/v2/models/{MODEL_NAME}", timeout=1)
    assert req.status_code == 200


def test_available_grpc():
    triton_client = grpcclient.InferenceServerClient(url=SERVER_GRPC)
    assert triton_client.is_model_ready(MODEL_NAME)


def test_inference():
    SEQUENCES = np.array(
        [
            ["AA"],
            ["PEPTIPEPTIR[UNIMOD:7]EPTIPEPTIPEPTIPEPT"],
            ["HKDER[UNIMOD:7]STNQC[UNIMOD:4]GAVILMFYW"],
            ["R[UNIMOD:7]HKDESTNQC[UNIMOD:4]GPAVILMFYW"],
            ["R[UNIMOD:7]HKDESTNQC[UNIMOD:4]GPAVILM[UNIMOD:35]FYW"],
        ],
        dtype=np.object_,
    )

    charge = np.array([[3] for _ in range(len(SEQUENCES))], dtype=np.int32)
    ces = np.array([[30] for _ in range(len(SEQUENCES))], dtype=np.float32)
    frag = np.array([["HCD"] for _ in range(len(SEQUENCES))], dtype=np.object_)

    triton_client = grpcclient.InferenceServerClient(url=SERVER_GRPC)

    in_pep_seq = grpcclient.InferInput("peptide_sequences", SEQUENCES.shape, "BYTES")
    in_pep_seq.set_data_from_numpy(SEQUENCES)

    in_charge = grpcclient.InferInput("precursor_charges", charge.shape, "INT32")
    in_charge.set_data_from_numpy(charge)

    in_ces = grpcclient.InferInput("collision_energies", ces.shape, "FP32")
    in_ces.set_data_from_numpy(ces)

    in_frag = grpcclient.InferInput("fragmentation_types", frag.shape, "BYTES")
    in_frag.set_data_from_numpy(frag)

    result = triton_client.infer(
        MODEL_NAME,
        inputs=[in_pep_seq, in_charge, in_ces, in_frag],
        outputs=[
            grpcclient.InferRequestedOutput("intensities"),
            grpcclient.InferRequestedOutput("mz"),
            grpcclient.InferRequestedOutput("annotation"),
        ],
    )

    intensities = result.as_numpy("intensities")
    fragmentmz = result.as_numpy("mz")
    annotation = result.as_numpy("annotation")

    assert intensities.shape == (5, 174)
    assert fragmentmz.shape == (5, 174)
    assert annotation.shape == (5, 174)

    # Assert intensities consistent
    assert np.allclose(
        intensities,
        np.load("test/Prosit/arr_Prosit_2024_intensity_cit_int.npy"),
        rtol=0,
        atol=1e-3,
        equal_nan=True,
    )
