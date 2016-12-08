"""
This is an example of a Dapper-compliant dataset.

"""
import unittest
from pydap.parsers.dds import build_dataset
from pydap.parsers.das import parse_das, add_attributes


DDS = """Dataset {
    Sequence {
        Float32 lat;
        Float64 time;
        Float32 lon;
        Int32 _id;
        Sequence {
            Float32 temp_qc;
            Float32 salinity_qc;
            Float32 oxygen;
            Float32 depth;
            Float32 temp;
            Float32 chlorophyll;
            Float32 salinity;
            Float32 oxygen_qc;
            Float32 pressure_qc;
            Float32 pressure;
            Float32 chlorophyll_qc;
        } profile;
        Structure {
            String title;
            String data_origin;
            String source;
            String Conventions;
            String country_code;
            String cruise;
            String cruise_number;
            String cast_number;
        } attributes;
        Structure {
            Structure {
                Float32 valid_range[2];
            } depth;
        } variable_attributes;
    } location;
    Structure {
        Float32 lon_range[2];
        Float32 lat_range[2];
        Float32 depth_range[2];
        Float64 time_range[2];
    } constrained_ranges;
} northPacific;"""

DAS = """Attributes {
    NC_GLOBAL {
        Int32 max_profiles_per_request 15000;
        Int32 total_profiles_in_dataset 1707616;
        String version "1.1.0";
        String owner "";
        String contact "";
        String Conventions "epic-insitu-1.0";
        Float64 lon_range 100.0, 289.180000305176;
        Float64 lat_range 1.20000004244503E-5, 90.0;
        Float64 depth_range 0.0, 10860.900390625;
        Float64 time_range -1.1432412E12, 1.10778048E12;
    }
    location._id {
        String long_name "sequence id";
        Int32 missing_value 2147483647;
        String units "";
    }
    location.lat {
        String units "degree_north";
        String long_name "latitude";
        Float32 missing_value NaN;
        String axis "Y";
    }
    location.profile.temp_qc {
        String units "";
        String long_name "temperature quality flag";
        Float32 missing_value NaN;
    }
    location.profile.salinity_qc {
        String units "";
        String long_name "salinity quality flag";
        Float32 missing_value NaN;
    }
    location.time {
        String units "msec since 1970-01-01 00:00:00 GMT";
        String long_name "time";
        Float64 missing_value NaN;
        String axis "T";
    }
    location.profile.oxygen {
        String units "ml/l";
        String long_name "oxygen";
        Float32 missing_value NaN;
    }
    location.profile.depth {
        String units "m";
        String long_name "depth";
        Float32 missing_value NaN;
        String axis "Z";
    }
    location.lon {
        String units "degree_east";
        String long_name "longitude";
        Float32 missing_value NaN;
        String axis "X";
    }
    location.profile.temp {
        String units "degc";
        String long_name "temperature";
        Float32 missing_value NaN;
    }
    location.profile.chlorophyll {
        String units "ug/l";
        String long_name "total chlorophyll";
        Float32 missing_value NaN;
    }
    location.profile.salinity {
        String units "psu";
        String long_name "salinity";
        Float32 missing_value NaN;
    }
    location.profile.oxygen_qc {
        String units "";
        String long_name "oxygen quality flag";
        Float32 missing_value NaN;
    }
    location.profile.pressure_qc {
        String units "";
        String long_name "pressure quality flag";
        Float32 missing_value NaN;
    }
    location.profile.pressure {
        String units "dbar";
        String long_name "pressure";
        Float32 missing_value NaN;
    }
    location.profile.chlorophyll_qc {
        String units "";
        String long_name "total chlorophyll quality flag";
        Float32 missing_value NaN;
    }
}"""


class TestDapper(unittest.TestCase):
    def setUp(self):
        dataset = build_dataset(DDS)
        attributes = parse_das(DAS)
        self.dataset = add_attributes(dataset, attributes)

    def test_parse(self):
        self.assertEqual(self.dataset.keys(),
                         ['location', 'constrained_ranges'])
