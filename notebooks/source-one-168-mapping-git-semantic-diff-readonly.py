# %% Source One 168-row Notebook Files vs authoritative Git — READ ONLY
# 2026-10-15. Complete one-cell script in EXISTING Snowflake DEV notebook.
# Does not reload Archer source, rebuild graph, run SQL, write DIM/FACT or COMMIT.
# Source values and Content IDs are neither accessed nor printed.
# SHA256 manifest contains *digests only*, never a copy of the private CSV.
import csv
import hashlib
import io
from collections import Counter

_GIT_BLOB = "b9f982c445f293f9b5d47cab565194aa29ef8770"
_COLS = ["SOURCE_FIELD_NAME","OSCAL_MODEL","OSCAL_ELEMENT_PATH","EXECUTION_STATUS","TRANSFORM_ID","SOURCE_KEY","NULL_POLICY","LINEAGE_REQUIRED","VALUE_SOURCE","VALUE_REQUIRED","ALLOWED_VALUES","VALUE_MAP","OTHER_REMARKS_TEMPLATE","ROLE_ID","ROLE_TITLE","REFERENCE_TYPE","LOOKUP_KEY","DESCRIPTION_REQUIRED"]
_EXPECTED = {
    "0522e6b2fb99948199fae89d": "6bdaf9090c1584642c3e2cab2d974a34",
    "0761c704b227163066b0e807": "73851a6aeb613e7fb6919a0d0d2f246d",
    "079d261c23a4db078187ddc6": "ce4ccc84b498089de09381e08c637ece",
    "07dcc702eba3454306deaab4": "39fb2691b2ebbbf78546890e58bc9142",
    "08b5904afd4834f4e0e6597d": "d462deed893d0f7e6d5437fb7ebbf4e6",
    "0927f4b2997d81ab4c0d99a4": "5ca6987c1f095a2d9e95201b5d0a3b5d",
    "09a50c498d8590a9b0972ceb": "37426a758ddbd3ed086bb694b7143f97",
    "0b40478da046a96a852d53e0": "500eb95b5796008f236d3801b8116894",
    "0c7f17e6da219cc0c8c8eca1": "e6694725efdc73b30528aa19eb0d093d",
    "0fad474d93664bc331923864": "138992ff738c8596fff2e8f7e44fe39d",
    "108f048c317de061edb3042d": "835dc4f0723cf7adcd28f799f4833441",
    "1477d426865903653f10f154": "7742727c254f7e95a531b5f93ee5ef68",
    "18201ecf3b5a98f199453835": "972a69e5dbfae60e606f91502eef5f3d",
    "1961bbc6bb2b039ac25ed6b6": "2f56ab9939fef3604cc393a145f21bfb",
    "19d8cfc5fde0485d2727de43": "09af01728e7cbdd32d8c2ee14d37a8b5",
    "1a461c69f9f449bc65f7a933": "a9a720593d8da6bc7797ef48eed2dc5f",
    "1a58e7c08994276758fca39f": "a5b5c744ddc10b13a825a06cb138f4fd",
    "1b8129d168b06d477704d81b": "3bd84b3833d8644215a795bc17d8a441",
    "1e1398293a1b9d0ddfc755ea": "2fcb8e72cba7eb553b245a148762e4a2",
    "1e6cf172da79bf5d8bed2773": "6e52df8a50a89b5c15288dbec0add458",
    "1f2915569a7018ff797118c2": "e3fa9dba12a36034f492a71619ee099e",
    "229b015e1ac17ade988da9a8": "397344041a8c4ba698e0944f5d20b8bc",
    "2302763908bab7fd03c130e8": "5507977a319d843ea145c9a85d5c3976",
    "24302c112a7b0cf6ea5864a2": "508a3fada38e737d827ad1110a5667ec",
    "259bb75e76ef6243068deb30": "58a24445964684904175ff889a195a4c",
    "259d538fdbb8c7d8ec9e4c20": "a4297077d04a83765b2c60a1402a05b1",
    "2633f710f0a89e1d1a8eda4d": "45e01cd00fb66143f5fdf3d97ab16e44",
    "26c38c215669f89f4c496bef": "78f236826f1a43c014b3630dedbf6662",
    "2aee0b536151ab9fdc508eaa": "0d36387eebf67fc4918e77f872183dc2",
    "2b8691fd57c2082f86448ba0": "2e3d41053815836813241727ddf664ff",
    "2b8a89411882ba4ae807a74c": "30c15055df27bdb24bd546e3e2c6ea7e",
    "2d77cd8e6391d0a36231e712": "1edcb7552b028f3288e301443bfee568",
    "2dd3ce15a84920be5eefc08e": "fc34d26646e499a7116ba70d85712d6d",
    "3132b465b8067694beb68161": "14030e7ab0b86a63b451aa0fca908a31",
    "336928f2ce5cecd01f2a9dff": "90f3a00c2461d33198a8af29a31bbb64",
    "3374bc0448b03e9c7c5c80b9": "be1a080240aa30605c16090cf6a53e7b",
    "343c55f088a9643119136c13": "40249d6b7c1527567d1acd7bfd5060bf",
    "34637656b9605db7e266f427": "19d5ed51abac48f3e5395e44829d3d95",
    "35511a4b8d9f011d45de21f6": "08f76bb70c1a15f5bb3d4a12059149ad",
    "3553957052619c1ee68b2a5c": "1fd14924b9b6c8d0986cc7110006daa0",
    "36614ca777f0922ae4cf542c": "dc332d9ffb5cd136afd9649853350a80",
    "3661aff45aabda00345417c5": "20e2a4f2e76642dc862ae1210c5e6c52",
    "36e8cd07cbdd8cd9f699f862": "981af53b2bc3e213cb76bc0b70f16058",
    "38e9876071ee85cf373c2dd2": "30338d9f28336b30f5dc4408c72885d2",
    "3c6311b315c28b0c8dd26bd2": "79c0c70a07a76140ea1063d628b91bc1",
    "3cf54fa3f0cbdba2f8eb1c1f": "65b2eb6ea31e9b7e201dca7ed7d64d38",
    "3d5ff80be30d385cc0b4b1ae": "34ffbf8e20be3110ddcbd1cbd9b92165",
    "3f2ed71f0a696f0173f532d6": "13984464c4686315b062dfd9060e48ac",
    "4250e15c500fd067eda47765": "b15e260eb474fd38e79333c4932877c6",
    "430e5a9924f0e817bc25ca21": "3272455d6670d6be0dc676237bbe1dbb",
    "43cf0f86b67aaeb548710c6c": "029152fbe4a4c21422240882d47e5475",
    "453ca9f89ea2f497ea05f4d7": "082ff224f4d9e8693a4777a98aafc344",
    "47ff76080c601df5f27b1f4e": "b9632fa93ab04d423b24dd918185f933",
    "49237b141ca0d835fee00e98": "5d45ff457ea857812e42bba124ff25b0",
    "4ad555bca484b87fe5a4f777": "eb6fe1a36f5a1cc2ce03e6e56d49ef87",
    "4f645ae751edaa9df48baeff": "8d1a114206b6b23624fa2e2fd08dade2",
    "502cef9cab7b5139798c9e30": "311cacf558d2176b4cd1909f9f263582",
    "533faf5cd16a0a0fc69d6b97": "bd3113ced1955ec69ac0aef4da42b399",
    "5491ebb496e7c06313afeaa1": "0755e6f8c252449346fc4b4d2798ea99",
    "573cd6215ba360a1838f7d67": "cbae4704a9f6f43a0e4ea73e06c03520",
    "58690b733738398845ee074f": "f3134419efb5fe796fad3ebec7b58576",
    "59dd9f31743830fbef6ff49c": "bc491cf7556b61538e53b1b190a6afeb",
    "5ae48e9fd6cd1a5df4a27389": "d8818efaa8342fdd015a8795b0532ea5",
    "5cc098a5eb74e0fdb1ab13b9": "43e5290c743395d707a85ba301c8655f",
    "5d129bb90581e0d32ae3b947": "b70ae275855a7d2e48104dfc0e427bb2",
    "5d8476c4671d8aa5ea3f9e2b": "78b140917d30e05d5781896bf7a3975d",
    "5d84c01737122486a85705e0": "3757fe6c1060495fa28c172da6bb8f12",
    "5e02854019948625faa9dfb9": "e67ec3b039110463050473c3aba85fc7",
    "5e4ca4bc40fb8329a45764ee": "646de323b83e9f8905b33586fddfe428",
    "5e7a9aed057c08a8288f7e5c": "9a31ff2fb5920bac7f3b58c174eadf31",
    "61b788e3fe05f5c8ecc618f8": "b38d5ac6ba44d2329d013b830a0b68fe",
    "645bab643bf2bf55618bef5f": "887468aed78986110076244dda677ea8",
    "6644fd288f01f59c229ee21d": "e94f3907495fb70b2a1255ff5a0f36c2",
    "6969decfaaa1d2d9999bb625": "b8bce694e706fd5c3eb3865d9950ff28",
    "6d5f762a07e6850547559246": "f5b8147d819bacd90538d5b0b809e84e",
    "6d92fbf4dcefceef043378d3": "cd819b129d3eedd6b2805796f30b493e",
    "6e5a6c957c4d6f6c597db81c": "6eb6bd8a5c229058cec0a66c2e5f6358",
    "775114495af8d6da9b1d2a57": "e3715d4e9aa480202864d63e8331846b",
    "78d7d30aaf1099e7e00909d8": "c9a19e28821330bbcff05a47519fb1ba",
    "792c8e1793b931fa0e6934e9": "58d493594b6b68d6199ee56c41e66f1c",
    "797a5ac1ac1241206dc62360": "82dfd47ee8fdcb1057542c805d5131e9",
    "798ef7a4ea0122a5c3b08cbe": "26b54951e1c5ccf1fbbec7b2c4f5c5ed",
    "7a54eaca2edfad4a5e0cc62c": "833bd8ea1c4de01cf229fc9e719921c4",
    "7a73f06a986247f1bf9657e8": "2612a2386829d96ae43f737f34751024",
    "7a8c15a92d40514a6d0cfe23": "d7384456c907e917859d0ee7f40af891",
    "7b2e5daf74ae480a97fb39cb": "3b383df2f5956bd44fbee366f1f1780d",
    "8094c63773fbb7ca63c06a53": "5fbf5f862a1f0a9468d4a2bea4e7ed14",
    "82c096e003ce609b6ac395f1": "01c85cf2ae3b805d69991cadf3a217e7",
    "838a9fa6ff6d1e3e6f102398": "24bef4641bc937472584aab032d4ed8b",
    "84c96d9dd04cf2d2ec4b7fb9": "034f45c409836f26b612e3c6342bb654",
    "857466c6102a0c37a6a931dd": "999a88acbdd8a4ceae79036af3570ed7",
    "876b7ccd9a85ca9de8eae9ab": "32cf2a7760f2949880ba525916fad738",
    "889af3550bb6b67b0b611b21": "8e9b2a1a40dcf973861a1ee178168689",
    "8ab43a114f53e7821a568856": "0dfea597e5132b6bf98033e02e929810",
    "8c7f42e86562815ce2d97aa7": "2b8cb1ddc4e061cc72d1d086a4376b34",
    "8fbacc9b997069061e085943": "12da9680528fde3f74df4ebe7b5fe13f",
    "90617dc2562839687720c77f": "eaf2ce0be78cf8697b34ba9826624274",
    "914ef0475a1ca8426161d69a": "9b04e9157842a09e5f5389a231d45dbb",
    "917734f76b8727ac2bf00038": "b5cc02b4904629246c4108a7e763672c",
    "9314e752ae0b7a2d71a0600f": "b7e0ac5884a5b586e9173de0f3e79147",
    "94c3260c311ce73de415cf64": "ee9f92fe2b81a40611fe60ecf00acc35",
    "94ff37c316bb3ba95db665d1": "5f158f618ad346ed7664fb505425c690",
    "95ddf5c40cda967800c64d9b": "bd4e88dc17040f1bfea7dc06544b0668",
    "990f66be6d94f998851513ac": "246fcd63fd1f9be97d7301bedbb9cbb1",
    "9a00af8115517a0b8349de36": "b061050c71673857f6aea48a50f0b472",
    "9ada6c991730d63e9f4d34d2": "da7ad60d50ab136208d9aa8c532af93f",
    "9b0ad0a7fedb596f9ef9d42b": "f0a722920d97d9fb0d17dec3ff0b0279",
    "9b94a2cd5d11367c7793878b": "c6f92b9d0a3cdd627049a1e487c35e6e",
    "9d0d86540c779de3ef3910f8": "3b3369fabbb516d1f2f2c1c9479a94ea",
    "9d8ab17d25bf1c988d8ff3ca": "24398fac533c77eac019fd3fdcc2742c",
    "9dde7b4dfbabf5d5ab384b0c": "958b714db9d5bd3d1ce57556ef3de407",
    "a3eb5909978f611727d5d7e1": "6efc576e75520bdddc20a43187c3ef8d",
    "a4ce3a0799027f410a1cb1b2": "23a68822d8e9ee9c73883ad15d93702e",
    "a70f3ee41f0b8b6a424b2067": "4b6808e1e14f28d0de748bedf5b785b4",
    "a740d7d6250a091ceeb844b3": "879e9d002a534e2785574bc03aa05ba7",
    "a82208d73a7ab7197fe67a0b": "ae08b8f7fd6e2c8d2372b5b96cb7b387",
    "aca22f614dba0748c71ffe2f": "11551aafacfc8ab9ec6000ca1bf942c6",
    "ad0dd729afa6801f1ef3f58a": "de49aa5866cf9a293ae4a24e1f0cbc05",
    "ae6f1e4bc8a9126a34ae2352": "6c87a3d707bf6696be5c440776b1565c",
    "aeaef3e7625f0c76c2951740": "f01a90092632dc28454137f4a18fa77f",
    "b06e98917dc6670b1e3a792f": "f58562b3b6665f50a4d183d6447bf424",
    "b1db852cc4ffa0d34fbc5160": "7525cdf12552b7f7835314b054374585",
    "b387cc3b03d9b96a34625804": "ce3aa979aa9f398c0dd0a12d0609f73f",
    "b49feea6b179021a1424a8ff": "16967d6a406197234591d8c050557547",
    "b4c226d775113d4d50a09368": "ab15207b1b1b5e3b3d2a0d4849025fa6",
    "bae87849a2c2f4da42a33b4e": "aeddaff3502f1592b736fccc5f9e86dd",
    "bb2af9479d0c4b3304c1f2ab": "cd070cd18a9050910ce6d8579c16c456",
    "bb699d5b574c5acbb0a8f1a9": "6eb5f146308f0b3e11eae7e3d5bc96f6",
    "bce16cc4d23bd40380b0c962": "9c7e9df63ea6d495759cbd648f39a442",
    "bf2a9c2d48297f7535c3ec8f": "25f5d4075fc008ffc749ac9640f92364",
    "bfc9b9a0d473ac7ac41fa5aa": "d19877a2334c5972bc02f2586964ee08",
    "c09500158bbdef1b450b4664": "986f705fd87e1db5fe3a6d79d94ba93a",
    "c892d819a2436ab47f9fb5d8": "fe1c4106c2f700a5a64f6f264d7432d1",
    "c925b8f823cafd23537e5919": "50e689ae4d07766ce7f7a9cf2dd086e4",
    "cba8c4aa647b916983fe2520": "3aab5af6dd699de768bdcbd3af2ab944",
    "cd16dbaee7cb5695d7a42d1c": "f1e65344953028ef4f877cc3d2d14904",
    "d2035bf8ad32658cc3e58305": "afb8e8e9175288f8cdd050b87d5f662e",
    "d33578e080f421131cce868d": "8abcb1907adde1b3a638fadd85bea333",
    "d35fd01f902179ad7c81b8a0": "05062713414fab39e384b4bb847b4c3e",
    "d5b8768ceb782f9688d698aa": "440cbd292c73db451adbea9f779b01a1",
    "d5e4f5a441411b837ca56837": "160353602a308a2d9b73b3a1c92f4657",
    "d86c048afbdc28f1d4504a8b": "88d47762e3bf3568a1eb65b7c6328cae",
    "d906bc92dc42c1399a2d1451": "73d5183d766934f1213425ef03735e3c",
    "d9071386c673412b842637a2": "b8d58c75a0b2b8a2e135bab7d45a8f06",
    "da4dd08e3d56a56913873ccd": "b0bf5380e5727711225b998349b618a9",
    "db05fff376290d69cc1e6ad5": "adac00395f1f2b5ba70caba22f06acb2",
    "ddd3026cc88f448a16508b52": "6be0ea7b85e5d4f9771935579636b36a",
    "ded9c1a792c93f82e3092796": "67f6481cc3ab8b3df1c019ca90208398",
    "e17fabe35dca47bdc193bf3c": "e401dc49260ceb7c0fc8fc85368876f1",
    "e23693f7b3c16d640f1cbf37": "3a9e66b67143f6c7cce2e0e40317c295",
    "e41f07e2c7fca740495c0f70": "f633b0560e85084e9d768b87e092d2e6",
    "e5932aca87ba8aa33bc183b6": "718e55b8b17d67c4f497ae04c0fca765",
    "e7e54312e22483987bf7f66c": "e7aed1a28ac8bafca9a33dd01a9ae300",
    "e9782cc2e8772109a375b3ee": "71dfa84526a5b2a322fb81b64edd2c7c",
    "ea8139fca5e32947b1e91e88": "aa30047eb4e17c205aff5427fa5765d8",
    "ef9daade319261653434628c": "6129f95708ab0911b1dfd8d24b44e9fd",
    "f2dc9a63ea318ac8eee6f808": "4bd3373ef7913e56b55ed4ce71f890d9",
    "f493281489ebb454fd1e40b6": "f1ec20bc085e7b31b0347105173f7edd",
    "f4f4ffe0bc3519e199937221": "9a9f273ee27c5250176ea49df16e42e8",
    "f500089e1717645730d8713c": "a7228c2dab4526ea1d312eecd79fa67c",
    "f6c0eced03f0fab62cc40051": "4138470252cd30f4c610efa300e3294e",
    "f82510f84c27387fe3bd9c84": "40e641016af76b7dfca5ba9862b16449",
    "f8387fa455d45645d0f62284": "4b779855a18c6a29b59cbdfc5359032e",
    "f92c2da3b092d1452a5ecf8f": "da73eb53cc31e2507b7f64a7a3048ddc",
    "fabbdb6fe35cd0d0723a7b3a": "f1ff8e7a2478378bdb16993cc2e61ebf",
    "facdc638b7b5f217a847515c": "4bfb491131ae06b8f807d3ba40649673",
    "fb0d6d079e892025d6a59a37": "144f8f4ab38df8c2af3316b210872fa6",
    "fe5083e4bb08172e3061f139": "9df5aa290a79b1450fd29d296070a00a"
}
_EXPECTED_AGGREGATE = "a039dc1e8d02155a5a6be08445ef3e44b60411048a4d9802a4b6caaeb7af7b60"


def _stop(ok, msg):
    if not ok:
        raise RuntimeError("SSP_GIT_MAPPING_RECONCILIATION_STOP_" + msg)


def _s(row, key):
    value = row.get(key, "")
    return "" if value is None else str(value)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _key(row):
    return _sha("\x1f".join(_s(row, k) for k in (
        "SOURCE_FIELD_NAME", "OSCAL_MODEL", "OSCAL_ELEMENT_PATH")))[:24]


def _sig(row):
    return _sha("\x1f".join(_s(row, k) for k in _COLS))[:32]


def _verify_rows(rows, label):
    found = {}
    duplicates = []
    for row in rows:
        key = _key(row)
        if key in found:
            duplicates.append(_s(row, "SOURCE_FIELD_NAME"))
        found[key] = _sig(row)
    good = sum(_EXPECTED.get(key) == digest for key, digest in found.items())
    changed = [(row.get("SOURCE_FIELD_NAME") or "(blank)") for row in rows
               if _EXPECTED.get(_key(row)) != _sig(row)]
    removed = len(set(_EXPECTED) - set(found))
    aggregate = _sha("\n".join(key + ":" + found[key] for key in sorted(found)))
    count_statuses = Counter(_s(row, "EXECUTION_STATUS") for row in rows)
    ci = [row for row in rows if _s(row, "OSCAL_MODEL") == "SSP - Control Implementation"]
    full = (len(rows) == 168 and not duplicates and removed == 0
            and not changed and good == 168
            and aggregate == _EXPECTED_AGGREGATE
            and dict(count_statuses) == {
                "APPROVED": 165, "DEFERRED": 2, "BLOCKED_IF_POPULATED": 1}
            and len(ci) == 50 and all(_s(r, "EXECUTION_STATUS") == "APPROVED"
                                      for r in ci))
    print(label + "_RECORDS:", len(rows))
    print(label + "_EXECUTABLE_RULES_MATCH_GIT:", full)
    print(label + "_MATCHED_RULES:", good)
    print(label + "_DIFFERING_RULES:", len(changed))
    print(label + "_MISSING_IDENTITIES:", removed)
    print(label + "_DUPLICATE_IDENTITIES:", len(duplicates))
    if changed:
        print(label + "_DIFFERING_FIELDS_MAX_20:", ", ".join(changed[:20]))
    return full, found


_stop("CONFIG" in globals() and CONFIG.get("EXECUTE_WRITES") is False,
      "WRITES_MUST_BE_FALSE")
_stop("SELECTED_MODELS" in globals() and tuple(SELECTED_MODELS) == ("SSP",),
      "SSP_ONLY")
_stop("MAPPING_INPUTS" in globals() and set(MAPPING_INPUTS) == {"source-one"},
      "CACHED_SOURCE_ONE_MAPPING_MISSING")
_stop("SOURCE_PROFILES" in globals(), "SOURCE_PROFILE_MISSING")
_profiles = [p for p in SOURCE_PROFILES if p.get("SOURCE_KEY") == "source-one"]
_stop(len(_profiles) == 1, "SOURCE_ONE_FILE_BINDING_AMBIGUOUS")
_path = _profiles[0].get("MAPPING_FILE")
_stop(isinstance(_path, str) and bool(_path), "MAPPING_FILENAME_MISSING")

print("SOURCE_ONE_GIT_168_MAPPING_SEMANTIC_RECONCILIATION_READ_ONLY")
print("AUTHORITATIVE_GIT_CSV_BLOB:", _GIT_BLOB)
_cached = MAPPING_INPUTS["source-one"]
_cached_match, _cached_signatures = _verify_rows(_cached, "CACHED")
_disk_match = None
_byte_match = None
_disk_signatures = None
try:
    with open(_path, "rb") as _file:
        _bytes = _file.read()
    _actual_blob = hashlib.sha1(
        ("blob %d\0" % len(_bytes)).encode("ascii") + _bytes
    ).hexdigest()
    _byte_match = _actual_blob == _GIT_BLOB
    _reader = csv.DictReader(io.StringIO(_bytes.decode("utf-8-sig"), newline=""))
    _header = list(_reader.fieldnames or [])
    _stop(set(_header) == set(_COLS) | {"NOTES"} and len(_header) == 19,
          "NOTEBOOK_FILE_COLUMNS_DIFFER")
    _rows = [row for row in _reader if any(v for v in row.values())]
    _disk_match, _disk_signatures = _verify_rows(_rows, "NOTEBOOK_FILE")
    print("NOTEBOOK_FILE_EXACT_GIT_BLOB_MATCH:", _byte_match)
    print("CACHED_RULES_MATCH_NOTEBOOK_FILE:",
          _cached_signatures == _disk_signatures)
except OSError:
    print("NOTEBOOK_FILE_READ_STATUS: FILE_UNAVAILABLE")
except UnicodeError:
    print("NOTEBOOK_FILE_READ_STATUS: INVALID_UTF8")
if _disk_match is True and _cached_match and _byte_match:
    _result = "EXACT_GIT_CSV_AND_CACHED_MAPPING_MATCH"
elif _disk_match is True and _cached_match and _byte_match is False:
    _result = "EXECUTABLE_MAPPINGS_MATCH_GIT__ONLY_NOTES_ORDER_OR_FORMAT_DIFFER"
elif _disk_match is True and not _cached_match:
    _result = "NOTEBOOK_FILE_RULES_CURRENT_BUT_CACHED_MAPPING_STALE"
elif _cached_match and _disk_match is False:
    _result = "CACHED_MAPPINGS_CURRENT_BUT_NOTEBOOK_FILE_DIFFERS"
else:
    _result = "REVIEW_REQUIRED_EXECUTABLE_MAPPING_OR_FILE_DIFFERENCE"
print("RESULT:", _result)
print("This comparison ignores NOTES and CSV row ordering, not execution columns.")
print("A rule match is NOT an exact file-loaded release fingerprint or COMMIT approval.")
print("NO RAW DATA READ, NO SOURCE VALUES OR CONTENT IDS, NO TARGET DIM/FACT DML.")
