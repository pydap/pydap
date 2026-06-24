"""Virtualizarr parser for dmrpp sidecar files produces by Hyrax"""

from __future__ import annotations

import base64
import io
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable
from xml.etree import ElementTree as ET

import numpy as np

import pydap.model
from pydap.parsers.dmr import DummyData

if TYPE_CHECKING:
    from obspec_utils.registry import ObjectStoreRegistry
    from virtualizarr.manifests import ManifestStore


def _require_virtualizarr():
    if sys.version_info < (3, 12):
        raise ImportError(
            "pydap.virtualizarr requires Python >=3.12 and the "
            "'virtualizarr' extra. Install it with: pip install 'pydap[virtualizarr]'"
        )

    try:
        from obspec_utils.readers import EagerStoreReader
        from obspec_utils.registry import ObjectStoreRegistry
        from virtualizarr.manifests import (
            ChunkManifest,
            ManifestArray,
            ManifestGroup,
            ManifestStore,
        )
        from virtualizarr.manifests.utils import create_v3_array_metadata
        from virtualizarr.parsers.utils import encode_cf_fill_value
    except ImportError as exc:
        raise ImportError(
            "pydap.virtualizarr requires the 'virtualizarr' extra. "
            "Install it with: pip install 'pydap[virtualizarr]'"
        ) from exc

    return (
        EagerStoreReader,
        ChunkManifest,
        ManifestArray,
        ManifestGroup,
        ManifestStore,
        ObjectStoreRegistry,
        create_v3_array_metadata,
        encode_cf_fill_value,
    )


class DMRParser:
    """
    Parser for the OPeNDAP DMR++ XML format.
    Reads groups, dimensions, coordinates, data variables, encoding, chunk manifests,
    and attributes. Highly modular to allow support for older dmrpp schema versions.
    Includes many utility functions to extract different information such as finding
    all variable tags, splitting hdf5 groups, parsing dimensions, and more.

    OPeNDAP DMR++ homepage: https://docs.opendap.org/index.php/DMR%2B%2B
    """

    # DAP and DMRPP XML namespaces
    _NS = {
        "dap": "http://xml.opendap.org/ns/DAP/4.0#",
        "dmrpp": "http://xml.opendap.org/dap/dmrpp/1.0.0#",
    }

    root: ET.Element
    data_filepath: str

    def __init__(
        self,
        url: str,
        object_store: "ObjectStoreRegistry",
        skip_variables: Iterable[str] | None = None,
    ):
        """
        Initialize the DMRParser with the given DMR++ file contents and source data file
        path.

        Parameters
        ----------
        url
            The URL of the DMR++ file.
        object_store
            The object store to use for reading data.
        skip_variables
            A list of variable names to skip during parsing.
        """

        EagerStoreReader, *_ = _require_virtualizarr()
        try:
            store, path_in_store = object_store.resolve(url)
            reader = EagerStoreReader(store=store, path=path_in_store)
            file_bytes = reader.readall()
            stream = io.BytesIO(file_bytes)
            self.root = ET.parse(stream).getroot()
            self.data_filepath = (
                url.removesuffix(".dap.dmrpp")
                if url.endswith(".dap.dmrpp")
                else url.removesuffix(".dmrpp")
            )
        except AttributeError:
            # object_store is a LocalStore (no .resolve method); url is either
            # a path to a local .dmr/.dmrpp file or a raw XML string.
            try:
                self.root = ET.fromstring(open(url).read())
            except OSError:
                self.root = ET.fromstring(url)
            self.data_filepath = f"file:///{self.root.attrib['name']}"
            store = object_store

        self.object_store = store
        self.skip_variables = skip_variables or ()
        self._validation_issues: list[str] = []

    def dmrparser(self):
        """Exposes the _DMRParser to external use (avoids breaking changes)"""
        parser = DMRPPParser(
            root=self.root,
            data_filepath=self.data_filepath,
            skip_variables=self.skip_variables,
        )
        self._validation_issues = parser._validation_issues
        return parser

    def parse_dataset(
        self,
        group: str | None = None,
    ) -> "ManifestStore":
        """
        Parses the given file and creates a ManifestStore.

        Parameters
        ----------
        group
            The group to parse. Ignored if no groups are present, and the entire
            dataset is parsed. If `None` or "/", and groups are present, the first group
            is parsed.  If not `None` or "/", and no groups are present, a UserWarning
            is issued indicating that the group will be ignored.

        Returns
        -------
        ManifestStore

        Examples
        --------
        Open a sample DMR++ file and parse the dataset
        """

        (
            EagerStoreReader,
            ChunkManifest,
            ManifestArray,
            ManifestGroup,
            ManifestStore,
            ObjectStoreRegistry,
            create_v3_array_metadata,
            encode_cf_fill_value,
        ) = _require_virtualizarr()

        group = group or "/"
        ngroups = len(self.root.findall("dap:Group", self._NS))

        if ngroups == 0 and group != "/":
            warnings.warn(
                f"No groups in DMR++ file {self.data_filepath!r}; "
                f"ignoring group parameter {group!r}"
            )

        group_path = Path("/") if ngroups == 0 else Path("/") / group.removeprefix("/")

        dataset_element = self.dmrparser()._split_groups(self.root).get(group_path)

        if dataset_element is None:
            raise ValueError(
                f"Group {group_path} not found in DMR++ file {self.data_filepath!r}"
            )

        # get two dictionary containing relevant metadata
        vars_dict, attrs = self.dmrparser()._parse_dataset(dataset_element)

        manifest_dict: dict[str, ManifestArray] = {}

        for var in vars_dict.keys():
            chunkmanifest = vars_dict[var].pop("chunkmanifest", None)
            # remove opendap-related metadata
            meta = dict(
                [
                    (k, v)
                    for k, v in vars_dict[var].items()
                    if k not in ["Maps", "fqn_dims"]
                ]
            )
            if "_FillValue" in meta["attributes"]:
                encoded_cf_fill_value = encode_cf_fill_value(
                    meta["attributes"]["_FillValue"], meta["data_type"]
                )
                meta["attributes"]["_FillValue"] = encoded_cf_fill_value

            if "inline" in meta:
                # extract data already decoded into array/string
                data = meta.pop("inline", None)
                bdata = base64.b64encode(data)

                chunks = {
                    "0.0": {
                        "path": "__inline__",
                        "offset": 0,
                        "length": len(bdata),
                        "data": bdata,
                    },
                }
                chunkmanifest = ChunkManifest(entries=chunks)
            else:
                chunkmanifest = ChunkManifest(chunkmanifest)

            metadata = create_v3_array_metadata(**meta)
            manifest_dict[var] = ManifestArray(
                metadata=metadata, chunkmanifest=chunkmanifest
            )

        manifest_group = ManifestGroup(arrays=manifest_dict, attributes=attrs)
        registry: ObjectStoreRegistry = ObjectStoreRegistry()
        registry.register(self.data_filepath, self.object_store)

        return ManifestStore(registry=registry, group=manifest_group)


class DMRPPParser:
    """
    Parser for the OPeNDAP DMR++ XML format.
    Reads groups, dimensions, coordinates, data variables, encoding, chunk manifests,
    and attributes. Highly modular to allow support for older dmrpp schema versions.
    Includes many utility functions to extract different information such as finding
    all variable tags, splitting hdf5 groups, parsing dimensions, and more.

    OPeNDAP DMR++ homepage: https://opendap.github.io/DMRpp-wiki/DMRpp.html
    """

    # DAP and DMRPP XML namespaces
    _NS = {
        "dap": "http://xml.opendap.org/ns/DAP/4.0#",
        "dmrpp": "http://xml.opendap.org/dap/dmrpp/1.0.0#",
        "xmlns": "http://www.w3.org/XML/1998/namespace",
    }
    # DAP data types to numpy data types
    _DAP_NP_DTYPE = {
        "Byte": "uint8",
        "UByte": "uint8",
        "Int8": "int8",
        "UInt8": "uint8",
        "Int16": "int16",
        "UInt16": "uint16",
        "Int32": "int32",
        "UInt32": "uint32",
        "Int64": "int64",
        "UInt64": "uint64",
        "Url": "object",
        "Float32": "float32",
        "Float64": "float64",
        "String": "object",
    }
    # Default zlib compression value
    _DEFAULT_ZLIB_VALUE = 6
    # Encoding keys that should be removed from attributes and placed in xarray
    # encoding dict
    # _ENCODING_KEYS = {"_FillValue", "missing_value", "scale_factor", "add_offset"}
    root: ET.Element
    data_filepath: str

    def __init__(
        self,
        root: ET.Element,
        data_filepath: str | None = None,
        skip_variables: Iterable[str] | None = None,
    ):
        """
        Initialize the DMRParser with the given DMR++ file contents and source data file
        path.

        Parameters
        ----------
        root
            Root of the xml tree structure of a DMR++ file.
        data_filepath
            The path to the actual data file that will be set in the chunk manifests.
            If None, the data file path is taken from the DMR++ file.
        """
        self.root = root
        self._validation_issues: list[str] = []
        data_filepath_from_root = self._get_attrib(self.root, "name", required=True)
        assert data_filepath_from_root is not None  # required=True guarantees non-None

        self.data_filepath = (
            data_filepath if data_filepath is not None else data_filepath_from_root
        )  # this may need change / must compare here
        self.skip_variables = skip_variables or ()
        self.opendap_url = self.root.attrib.get("{" + self._NS["xmlns"] + "}base")

    def _get_attrib(
        self, element: ET.Element, attrib_name: str, required: bool = False
    ) -> str | None:
        """
        Safely get an attribute from an XML element, logging validation issues.

        Parameters
        ----------
        element
            The XML element to get the attribute from.
        attrib_name
            The name of the attribute to get.
        required
            If True, raises a ValueError when the attribute is missing. If False,
            returns None and logs the issue.

        Returns
        -------
        str | None
            The attribute value if found, None otherwise.

        Raises
        ------
        ValueError
            If required is True and the attribute is not found.
        """
        if attrib_name in element.attrib:
            return element.attrib[attrib_name]

        element_info = (
            element.tag
            if "name" not in element.attrib
            else f"{element.tag}[@name='{element.attrib['name']}']"
        )
        issue_msg = (
            f"Missing required attribute '{attrib_name}' in element: {element_info}"
        )
        self._validation_issues.append(issue_msg)

        if required:
            raise ValueError(issue_msg)

        return None

    def to_dataset(self):
        """Parses the DMRpp element and translates it to the Pydap dataset model"""
        Groups = [str(item) for item in self._split_groups(self.root).keys()]
        dimensions = {}
        dim_tags = self._find_dimension_tags(self.find_node_fqn(Groups[0]))

        pyds = pydap.model.DatasetType(
            name=self.root.get("name"), dimensions=dimensions
        )

        metadata, attrs = self._parse_dataset(self.find_node_fqn(Groups[0]))
        # order of serialization
        for var in metadata.keys():
            data = DummyData(
                dtype=metadata[var]["data_type"],
                shape=metadata[var]["shape"],
                path=Groups[0],
            )
            pyds.createVariable(
                name=var,
                data=data,
                dims=metadata[var]["fqn_dims"],
                Maps=metadata[var]["Maps"],
                attributes=metadata[var].pop("attributes"),
            )

        for gr in Groups[1:]:
            metadata, attrs = self._parse_dataset(self.find_node_fqn(gr))
            dimensions = {}
            dim_tags = self._find_dimension_tags(self.find_node_fqn(gr))
            for dim in dim_tags:
                dimensions.update(self._parse_dim(dim))

            pyds.createGroup(name=gr, dimensions=dimensions, attributes=attrs)

            for var in metadata.keys():
                data = DummyData(
                    dtype=metadata[var]["data_type"],
                    shape=metadata[var]["shape"],
                    path=gr,
                )
                pyds.createVariable(
                    name=gr + "/" + var,
                    data=data,
                    dims=metadata[var]["fqn_dims"],
                    Maps=metadata[var]["Maps"],
                    attributes=metadata[var].pop("attributes"),
                )
        return pyds

    def parse_dataset(
        self,
        group: str | None = None,
    ):
        """
        Parses the given file and creates a ManifestStore.

        Parameters
        ----------
        group
            The group to parse. Ignored if no groups are present, and the entire
            dataset is parsed. If `None` or "/", and groups are present, the first group
            is parsed.  If not `None` or "/", and no groups are present, a UserWarning
            is issued indicating that the group will be ignored.

        Returns
        -------
        ManifestStore

        Examples
        --------
        Open a sample DMR++ file and parse the dataset
        """
        group = group or "/"
        ngroups = len(self.root.findall("dap:Group", self._NS))

        if ngroups == 0 and group != "/":
            warnings.warn(
                f"No groups in DMR++ file {self.data_filepath!r}; "
                f"ignoring group parameter {group!r}"
            )

        group_path = Path("/") if ngroups == 0 else Path("/") / group.removeprefix("/")
        dataset_element = self._split_groups(self.root).get(group_path)

        if dataset_element is None:
            raise ValueError(
                f"Group {group_path} not found in DMR++ file {self.data_filepath!r}"
            )

        return self._parse_dataset(dataset_element)

    def find_node_fqn(self, fqn: str) -> ET.Element:
        """
        Find the element in the root element by converting the fully qualified name to
        an xpath query.

        E.g. fqn = "/a/b" --> root.find("./*[@name='a']/*[@name='b']")

        See more about OPeNDAP fully qualified names (FQN) here:
        https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1#Fully_Qualified_Names

        Parameters
        ----------
        fqn
            The fully qualified name of an element. For example, "/a/b".

        Returns
        -------
        ET.Element
            The matching node found within the root element.

        Raises
        ------
        ValueError
            If the fully qualified name is not found in the root element.
        """
        if fqn == "/":
            return self.root

        elements = fqn.strip("/").split("/")  # /a/b/ --> ['a', 'b']
        xpath_segments = [f"*[@name='{element}']" for element in elements]
        xpath_query = "/".join([".", *xpath_segments])  # "./[*[@name='a']/*[@name='b']"

        if (element := self.root.find(xpath_query, self._NS)) is None:
            raise ValueError(f"Path {fqn} not found in provided root")

        return element

    def _split_groups(self, root: ET.Element) -> dict[Path, ET.Element]:
        """
        Split the input <Dataset> element into several <Dataset> ET.Elements by <Group>
        name.
        E.g. {"/": <Dataset>, "left": <Dataset>, "right": <Dataset>}

        Parameters
        ----------
        root : ET.Element
            The root element of the DMR file.

        Returns
        -------
        dict[Path, ET.Element]
        """
        all_groups: dict[Path, ET.Element] = {}
        dataset_tags = [
            d for d in root if d.tag != "{" + self._NS["dap"] + "}" + "Group"
        ]
        if len(dataset_tags) > 0:
            all_groups[Path("/")] = ET.Element(root.tag, root.attrib)
            all_groups[Path("/")].extend(dataset_tags)
        all_groups.update(self._split_groups_recursive(root, Path("/")))
        return all_groups

    def _split_groups_recursive(
        self, root: ET.Element, current_path=Path("")
    ) -> dict[Path, ET.Element]:
        group_dict: dict[Path, ET.Element] = {}
        for g in root.iterfind("dap:Group", self._NS):
            group_name = self._get_attrib(g, "name", required=True)
            if group_name is None:
                continue
            new_path = current_path / Path(group_name)
            dataset_tags = [
                d for d in g if d.tag != "{" + self._NS["dap"] + "}" + "Group"
            ]
            group_dict[new_path] = ET.Element(g.tag, g.attrib)
            group_dict[new_path].extend(dataset_tags)
            group_dict.update(self._split_groups_recursive(g, new_path))
        return group_dict

    def _parse_dataset(
        self,
        root: ET.Element,
    ):
        """
        Parse the dataset using the root element of the DMR++ file.

        Parameters
        ----------
        root : ET.Element
            The root element of the DMR++ file.

        Returns
        -------
        ManifestGroup
        """

        manifest_dict: dict[str, Any] = {}
        for var_tag in self._find_var_tags(root):
            var_name = self._get_attrib(var_tag, "name")
            if var_name and var_name not in self.skip_variables:
                try:
                    variable = self._parse_variable(var_tag)
                    manifest_dict[var_name] = variable
                except (UnboundLocalError, ValueError):
                    warnings.warn(
                        f"This DMRpp contains the variable {var_name} that could not"
                        " be parsed. Consider adding it to the list  of skipped "
                        "variables, or opening an issue to help resolve this"
                    )

        # Attributes
        attrs: dict[str, str] = {}
        # Look for an attribute tag called "HDF5_GLOBAL" and unpack it
        hdf5_global_attrs = root.find("dap:Attribute[@name='HDF5_GLOBAL']", self._NS)
        if hdf5_global_attrs is not None:
            # Remove the container attribute and add its children to the root dataset
            root.remove(hdf5_global_attrs)
            root.extend(hdf5_global_attrs)
        # remove dmrpp build attribute (only appears at root-level)
        dmrpp_build_attr = root.find(
            "dap:Attribute[@name='build_dmrpp_metadata']", self._NS
        )
        if dmrpp_build_attr is not None:
            root.remove(dmrpp_build_attr)
        cattrs = root.findall("dap:Attribute[@type='Container']", self._NS)
        for attr in cattrs:
            root.remove(attr)
            root.extend(attr)
        for attr_tag in root.iterfind("dap:Attribute", self._NS):
            attrs.update(self._parse_attribute(attr_tag))
        return manifest_dict, attrs

    def _find_var_tags(self, root: ET.Element) -> list[ET.Element]:
        """
        Find all variable tags in the DMR++ file. Also known as array tags.
        Tags are labeled with the DAP data type. E.g. <Float32>, <Int16>, <String>

        Parameters
        ----------
        root : ET.Element
            The root element of the DMR++ file.

        Returns
        -------
        list[ET.Element]
        """
        vars_tags: list[ET.Element] = []
        for dap_dtype in self._DAP_NP_DTYPE:
            vars_tags += root.findall(f"dap:{dap_dtype}", self._NS)
        return vars_tags

    def _parse_dim(self, root: ET.Element, dim_index: int = 0) -> dict[str, int]:
        """
        Parse single <Dim> or <Dimension> tag

        If the tag has no name attribute, it is a phony dimension.
        E.g. <Dim size="300"/> --> {"phony_dim_0": 300}
        If the tag has both name and size attributes, it is a regular dimension.
        E.g. <Dim name="lat" size="1447"/> --> {"lat": 1447}

        Parameters
        ----------
        root : ET.Element
            The root element Dim/Dimension tag
        dim_index : int
            Index of the dimension, used for naming phony dimensions

        Returns
        -------
        dict
            E.g. {"time": 1, "lat": 1447, "lon": 2895}, {"phony_dim_0": 300},
            {"time": None, "lat": None, "lon": None}
        """
        size_attr = self._get_attrib(root, "size")
        name_attr = self._get_attrib(root, "name")

        if size_attr is not None:
            size = int(size_attr)
            if name_attr is not None:
                return {Path(name_attr).name: size}
            else:
                return {f"phony_dim_{dim_index}": size}

        raise ValueError("Not enough information to parse Dim/Dimension tag")

    def _find_dimension_tags(self, root: ET.Element) -> list[ET.Element]:
        """
        Find the all tags with dimension information.

        First attempts to find Dimension tags, then falls back to Dim tags.
        If Dim tags are found, the fully qualified name is used to find the
        corresponding Dimension tag.

        Parameters
        ----------
        root : ET.Element
            An ElementTree Element from a DMR++ file.

        Returns
        -------
        list[ET.Element]
        """
        dimension_tags = root.findall("dap:Dimension", self._NS)
        if not dimension_tags:
            # Dim tags contain a fully qualified name that references a
            # Dimension tag elsewhere in the DMR++
            # or they are phony dimensions (have size but no name)
            dim_tags = root.findall("dap:Dim", self._NS)
            for d in dim_tags:
                dim_name = self._get_attrib(d, "name")
                if dim_name is not None:
                    dimension_tag = self.find_node_fqn(dim_name)
                    if dimension_tag is not None:
                        dimension_tags.append(dimension_tag)
                else:
                    # Phony dimension - use the Dim tag directly
                    dimension_tags.append(d)
        return dimension_tags

    def _find_dim_tags(self, root: ET.Element) -> list[ET.Element]:
        """
        Find the all Dim tags with fully qualifying names.

        Parameters
        ----------
        root : ET.Element
            An ElementTree Element from a DMR++ file.

        Returns
        -------
        list[ET.Element]
        """
        dimension_tags = root.findall("dap:Dimension", self._NS)
        if not dimension_tags:
            # Dim tags contain a fully qualified name that references a Dimension tag
            #  elsewhere in the DMR++
            dim_tags = root.findall("dap:Dim", self._NS)
            for d in dim_tags:
                dimension_tag = self.find_node_fqn(d.attrib["name"])
                if dimension_tag is not None:
                    dimension_tags.append(dimension_tag)
        return dimension_tags

    def _parse_variable(self, var_tag: ET.Element):
        """
        Parse a variable from a DMR++ tag.

        Parameters
        ----------
        var_tag : ET.Element
            An ElementTree Element representing a variable in the DMR++ file. Will have
            DAP dtype as tag. E.g. <Float32>

        Returns
        -------
        ManifestArray
        """

        # Dimension info
        dims: dict[str, int] = {}
        dimension_tags = self._find_dimension_tags(var_tag)
        for dim_index, dim in enumerate(dimension_tags):
            dims.update(self._parse_dim(dim, dim_index=dim_index))

        # convert DAP dtype to numpy dtype
        dtype = np.dtype(
            self._DAP_NP_DTYPE[var_tag.tag.removeprefix("{" + self._NS["dap"] + "}")]
        )
        # Chunks and Filters
        shape: tuple[int, ...] = tuple(dims.values())
        inline_value: str | None = None
        chunks_shape = shape
        chunks_tag = var_tag.find("dmrpp:chunks", self._NS)
        array_fill_value = np.array(0).astype(dtype)[()]
        miss_val_tag = var_tag.find("dmrpp:missingdata", self._NS)
        compact_tag = var_tag.find("dmrpp:compact", self._NS)
        if miss_val_tag is not None:
            missing_bytes = pydap.lib.decode_missingdata(miss_val_tag.text)
            inline_value = np.frombuffer(missing_bytes, dtype=dtype)
            codecs = None
            chunkmanifest = {}
        if compact_tag is not None:
            missing_bytes = pydap.lib.decode_compact(compact_tag.text)
            inline_value = np.frombuffer(missing_bytes, dtype=dtype)

        if chunks_tag is not None:
            # Chunks
            chunk_dim_text = chunks_tag.findtext(
                "dmrpp:chunkDimensionSizes", namespaces=self._NS
            )
            if chunk_dim_text is not None:
                # 1 1447 2895 -> (1, 1447, 2895)
                chunks_shape = tuple(map(int, chunk_dim_text.split()))
            else:
                chunks_shape = shape
            fill_value = self._get_attrib(chunks_tag, "fillValue")
            if fill_value is not None:
                array_fill_value = np.array(fill_value).astype(dtype)[()]
            if chunks_shape:
                chunkmanifest = self._parse_chunks(chunks_tag, chunks_shape)
            else:
                # there could a scalar with chunk element with offset/nbytes attrs
                c_attrs = [c.attrib for c in chunks_tag]
                if len(c_attrs) > 0 and "nBytes" in c_attrs[0].keys():
                    c_attrs = c_attrs[0]
                    chunkmanifest = self._parse_chunks(
                        chunks_tag, (c_attrs["nBytes"][0])
                    )
                else:
                    chunkmanifest = {"entries": {}, "shape": array_fill_value.shape}
            # Filters
            codecs = self._parse_filters(chunks_tag, dtype)
        # Attributes
        attrs: dict[str, Any] = {}
        cattrs = var_tag.findall("dap:Attribute[@type='Container']", self._NS)
        for attr in cattrs:
            var_tag.remove(attr)
            var_tag.extend(attr)
        for attr_tag in var_tag.iterfind("dap:Attribute", self._NS):
            attrs.update(self._parse_attribute(attr_tag))

        # if "_FillValue" in attrs:
        # encoded_cf_fill_value = encode_cf_fill_value(attrs["_FillValue"], dtype)
        # attrs["_FillValue"] = encoded_cf_fill_value
        metadata: dict[str, Any] = {}
        # creates array v3 in virtualizarr
        metadata.update(
            shape=shape,
            data_type=dtype,
            chunk_shape=chunks_shape,
            codecs=codecs,
            dimension_names=list(dims),
            fqn_dims=[dim.get("name") for dim in var_tag.findall("dap:Dim", self._NS)],
            Maps=[map.get("name") for map in var_tag.findall("dap:Map", self._NS)],
            attributes=attrs,
            fill_value=array_fill_value,
            chunkmanifest=chunkmanifest,
        )
        if inline_value is not None:
            metadata.update(inline=inline_value)
        return metadata

    def _parse_attribute(self, attr_tag: ET.Element) -> dict[str, Any]:
        """
        Parse an attribute from a DMR++ attr tag. Converts the attribute value to a
        native python type.
        Raises an exception if nested attributes are passed. Container attributes must
        be unwrapped in the parent function.

        Parameters
        ----------
        attr_tag : ET.Element
            An ElementTree Element with an <Attr> tag.

        Returns
        -------
        dict
        """
        attr: dict[str, Any] = {}
        values = []
        attr_type = self._get_attrib(attr_tag, "type")
        attr_name = self._get_attrib(attr_tag, "name", required=True)

        if attr_name is None:
            return {}

        if attr_type is None:
            return {}

        dtype = np.dtype(self._DAP_NP_DTYPE[attr_type])
        # if multiple Value tags are present, store as "key": "[v1, v2, ...]"
        for value_tag in attr_tag:
            # cast attribute to native python type using dmr provided dtype
            val = (
                dtype.type(value_tag.text).item()
                if dtype != np.object_
                else value_tag.text
            )
            # "*" may represent nan values in DMR++
            if val == "*":
                val = np.nan
            values.append(val)
        attr[attr_name] = values[0] if len(values) == 1 else values
        return attr

    def _parse_filters(
        self, chunks_tag: ET.Element, dtype: np.dtype
    ) -> list[dict] | None:
        """
        Parse filters from a DMR++ chunks tag.

        Parameters
        ----------
        chunks_tag : ET.Element
            An ElementTree Element with a <chunks> tag.

        dtype : np.dtype
            The numpy dtype of the variable.

        Returns
        -------
        list[dict] | None
            E.g. [{"id": "shuffle", "elementsize": 4}, {"id": "zlib", "level": 4}]
        """
        compression_type = self._get_attrib(chunks_tag, "compressionType")
        if compression_type is not None:
            filters: list[dict] = []
            # shuffle deflate --> ["shuffle", "deflate"]
            compression_types = compression_type.split(" ")
            for c in compression_types:
                if c == "shuffle":
                    filters.append(
                        {
                            "name": "numcodecs.shuffle",
                            "configuration": {"elementsize": dtype.itemsize},
                        }
                    )
                elif c == "deflate":
                    deflate_level = self._get_attrib(chunks_tag, "deflateLevel")
                    level = (
                        int(deflate_level)
                        if deflate_level is not None
                        else self._DEFAULT_ZLIB_VALUE
                    )
                    filters.append(
                        {
                            "name": "numcodecs.zlib",
                            "configuration": {
                                "level": level,
                            },
                        }
                    )
            return filters
        return None

    def _parse_chunks(
        self, chunks_tag: ET.Element, chunks_shape: tuple[int, ...]
    ) -> dict[str, object]:
        """
        Parse the chunk manifest from a DMR++ chunks tag.

        Parameters
        ----------
        chunks_tag : ET.Element
            An ElementTree Element with a <chunks> tag.

        chunks_shape : tuple
            Chunk sizes for each dimension. E.g. (1, 1447, 2895)

        Returns
        -------
        dict
        """
        chunkmanifest: dict[str, object] = {}
        default_num: list[int] = (
            [0 for i in range(len(chunks_shape))] if chunks_shape else [0]
        )
        path: str = None
        chunk_key_template = ".".join(["{}" for i in range(len(default_num))])
        for chunk_tag in chunks_tag.iterfind("dmrpp:chunk", self._NS):
            chunk_num = default_num
            chunk_position = self._get_attrib(chunk_tag, "chunkPositionInArray")
            if chunk_position is not None:
                # "[0,1023,10235]" -> ["0","1023","10235"]
                chunk_pos = chunk_position[1:-1].split(",")
                # [0,1023,10235] // [1, 1023, 2047] -> [0,1,5]
                chunk_num = [
                    int(chunk_pos[i]) // chunks_shape[i]
                    for i in range(len(chunks_shape))
                ]
            if "href" in chunk_tag.attrib:
                path = chunk_tag.attrib["href"]
            path = path if path is not None else self.data_filepath
            # [0,1,5] -> "0.1.5"
            chunk_key = chunk_key_template.format(*chunk_num)
            offset = self._get_attrib(chunk_tag, "offset", required=True)
            n_bytes = self._get_attrib(chunk_tag, "nBytes", required=True)
            if offset is not None and n_bytes is not None:
                chunkmanifest[chunk_key] = {
                    "path": path,
                    "offset": int(offset),
                    "length": int(n_bytes),
                }
        return chunkmanifest
