import json
import os
import uuid
from datetime import timedelta

from django.core.files.base import File as djangoFile
from django.contrib.auth.models import User, AnonymousUser
from django.db.models import Q, Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page, never_cache
from django_sendfile import sendfile
from filters.mixins import FiltersMixin
from rest_flex_fields import is_expanded
from rest_flex_fields.views import FlexFieldsMixin
from rest_framework import viewsets, filters, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
import pandas as pd
from rest_framework_simplejwt.tokens import AccessToken
from uniprotparser.betaparser import UniprotParser
import numpy as np
from rest_framework import status
from django.db import transaction
import io

from celsus.models import CellType, TissueType, ExperimentType, Instrument, Organism, OrganismPart, \
    QuantificationMethod, Project, Author, File, Keyword, Disease, Curtain, DifferentialSampleColumn, RawSampleColumn, \
    DifferentialAnalysisData, RawData, Comparison, GeneNameMap, LabGroup, UniprotRecord, ProjectSettings, \
    CurtainAccessToken, KinaseLibraryModel, DataFilterList
from celsus.permissions import IsOwnerOrReadOnly, IsFileOwnerOrPublic, IsCurtainOwnerOrPublic, HasCurtainToken, \
    IsCurtainOwner, IsNonUserPostAllow, IsDataFilterListOwner
from celsus.serializers import CellTypeSerializer, TissueTypeSerializer, ExperimentTypeSerializer, InstrumentSerializer, \
    OrganismSerializer, OrganismPartSerializer, QuantificationMethodSerializer, UserSerializer, ProjectSerializer, \
    AuthorSerializer, FileSerializer, KeywordSerializer, DifferentialSampleColumnSerializer, RawSampleColumnSerializer, \
    DifferentialAnalysisDataSerializer, RawDataSerializer, DiseaseSerializer, CurtainSerializer, ComparisonSerializer, \
    GeneNameMapSerializer, LabGroupSerializer, UniprotRecordSerializer, ProjectSettingsSerializer, \
    KinaseLibrarySerializer, DataFilterListSerializer
from celsus.utils import is_user_staff, delete_file_related_objects, calculate_boxplot_parameters, \
    check_nan_return_none, get_uniprot_data
from celsus.validations import organism_query_schema, differential_data_query_schema, raw_data_query_schema, \
    comparison_query_schema, project_query_schema, gene_name_map_query_schema, uniprot_record_query_schema, \
    curtain_query_schema, kinase_library_query_schema, data_filter_list_query_schema
from celsusdjango import settings


class ProjectSettingsViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = ProjectSettings.objects.all()
    serializer_class = ProjectSettingsSerializer

class UniprotRecordViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = UniprotRecord.objects.all()
    serializer_class = UniprotRecordSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "entry")
    ordering = ("id",)
    filter_mappings = {
        "id": "id",
        "entry": "entry"
    }

    filter_validation_schema = uniprot_record_query_schema

class CellTypeViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = CellType.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = CellTypeSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema

class TissueTypeViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = TissueType.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = TissueTypeSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema

class ExperimentTypeViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = ExperimentType.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = ExperimentTypeSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema

class InstrumentViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = Instrument.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = InstrumentSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema

class OrganismViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = Organism.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = OrganismSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains",
        "project_count": "project_count__gte"
    }
    filter_validation_schema = organism_query_schema
    #filterset_fields = ["name"]


class OrganismPartViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = OrganismPart.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = OrganismPartSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema

class QuantificationMethodViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = QuantificationMethod.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = QuantificationMethodSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema


    @action(methods=["get"], detail=True)
    def get_projects(self, request, pk=None):
        qm = self.get_object()
        projects = Project.objects.filter(quantification_method=qm)
        project_json = ProjectSerializer(projects, many=True)
        return Response(project_json.data)


class UserViewSet(FlexFieldsMixin, FiltersMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if is_expanded(self.request, 'project'):
            self.queryset = self.queryset.prefetch_related('project')
        if is_expanded(self.request, 'curtain'):
            self.queryset = self.queryset.prefetch_related('curtain')

        return self.queryset




class DiseaseViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = Disease.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = DiseaseSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema


class ProjectViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsOwnerOrReadOnly | permissions.IsAdminUser,]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "date")
    ordering = ("id",)
    filter_mappings = {
        "id": "id",
        "title": "title__icontains",
        "ids": "pk__in",
        "owner_ids": "owners__pk__in",
        "project_type": "project_type__in",
    }
    filter_validation_schema = project_query_schema

    def get_queryset(self):

        if is_expanded(self.request, 'default_settings'):

            self.queryset = self.queryset.select_related("default_settings")
        search_query = self.request.query_params.get("search_query", "")
        search_in = self.request.query_params.get("search_in", "")
        is_staff = is_user_staff(self.request)
        # check if search
        if search_in != "" and search_query != "":
            query = Q()
            extra_params = search_in.split(",")
            for i in extra_params:
                if i == "title":
                    query.add(Q(title__icontains=search_query), Q.OR)
                elif i == "description":
                    query.add(Q(description__icontains=search_query), Q.OR)
                elif i == "keyword":
                    query.add(Q(keyword__name__icontains=search_query), Q.OR)
                elif i == "associated_authors":
                    query.add(Q(associated_authors__name__icontains=search_query), Q.OR)
                elif i == "organism":
                    query.add(Q(organism__name__icontains=search_query), Q.OR)
                elif i == "accession_id":
                    query.add(Q(files__raw_datas__gene_names__accession_id__icontains=search_query), Q.OR)
                elif i == "gene_names":
                    query.add(Q(files__raw_datas__gene_names__gene_names__icontains=search_query), Q.OR)
                elif i == "lab_group":
                    query.add(Q(labgroup__name__icontains=search_query), Q.OR)

            if is_staff:
                return self.queryset.filter(query).distinct()
            return self.queryset.filter(query).filter(enable=True).distinct()
        if is_staff:
            return self.queryset
        return Project.objects.filter(enable=True).distinct()

    def create(self, request, *args, **kwargs):
        project = Project()
        for i in Project._meta.fields:
            if i.name in self.request.data:
                if getattr(project, i.name) != self.request.data[i.name]:
                    setattr(project, i.name, self.request.data[i.name])
        project.save()

        for i in self.request.data:
            if i == "cell_type":
                update_section(project.cell_type, self.request.data[i], CellType)
            elif i == "quantification_method":
                update_section(project.quantification_method, self.request.data[i], QuantificationMethod)
            elif i == "tissue_type":
                update_section(project.tissue_type, self.request.data[i], TissueType)
            elif i == "disease":
                update_section(project.disease, self.request.data[i], Disease)
            elif i == "instrument":
                update_section(project.instrument, self.request.data[i], Instrument)
            elif i == "keyword":
                update_section(project.keyword, self.request.data[i], Keyword)
            elif i == "organism":
                update_section(project.organism, self.request.data[i], Organism)
            elif i == "organism_part":
                update_section(project.organism_part, self.request.data[i], OrganismPart)
            elif i == "curtain":
                update_section(project.curtain, self.request.data[i], Curtain)
            elif i == "experiment_type":
                update_section(project.experiment_type, self.request.data[i], ExperimentType)
            elif i == "associated_authors":
                update_section(project.associated_authors, self.request.data[i], Author)
            elif i == "lab_group":
                update_section(project.lab_group, self.request.data[i], LabGroup)
        if "first_authors" in self.request.data:
            if len(self.request.data["first_authors"]) > 0:
                update_section(project.first_authors, self.request.data["first_authors"], Author)
        if self.request.user:
            project.owners.add(self.request.user)
        if project.project_type == "PTM":
            project.ptm_data = True
        project.default_settings = ProjectSettings()
        project.default_settings.save()
        project.save()
        project_json = ProjectSerializer(project, context={'request': request})
        pro = project_json.data
        pro["id"] = project.id

        return Response(pro)

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        for i in self.request.data:
            if i == "cell_type":
                update_section(project.cell_type, self.request.data[i], CellType)
            elif i == "quantification_method":
                update_section(project.quantification_method, self.request.data[i], QuantificationMethod)
            elif i == "tissue_type":
                update_section(project.tissue_type, self.request.data[i], TissueType)
            elif i == "disease":
                update_section(project.disease, self.request.data[i], Disease)
            elif i == "instrument":
                update_section(project.instrument, self.request.data[i], Instrument)
            elif i == "keyword":
                update_section(project.keyword, self.request.data[i], Keyword)
            elif i == "organism":
                update_section(project.organism, self.request.data[i], Organism)
            elif i == "organism_part":
                update_section(project.organism_part, self.request.data[i], OrganismPart)
            elif i == "curtain":
                update_section(project.curtain, self.request.data[i], Curtain)
            elif i == "experiment_type":
                update_section(project.experiment_type, self.request.data[i], ExperimentType)
            elif i == "disease":
                update_section(project.disease, self.request.data[i], Disease)
            elif i == "associated_authors":
                update_section(project.associated_authors, self.request.data[i], Author)
            elif i == "lab_group":
                update_section(project.lab_group, self.request.data[i], LabGroup)
        d = {}
        for i in Project._meta.fields:
            if i.name in self.request.data:
                if getattr(project, i.name) != self.request.data[i.name]:
                    setattr(project, i.name, self.request.data[i.name])
        if d:
            project.update(**d)
        project.save()
        project_json = ProjectSerializer(project, context={'request': request})
        return Response(project_json.data)

    @action(methods=["post"], detail=True, permission_classes=[permissions.IsAuthenticated & (IsOwnerOrReadOnly | permissions.IsAdminUser)])
    def set_file(self, request, pk=None):
        project = self.get_object()
        file = File.objects.filter(pk=self.request.data["file_id"]).first()
        project.files.add(file)
        project.save()
        project_json = ProjectSerializer(project, context={'request': request})
        project_json.data["id"] = project.id
        return Response(project_json.data)

    @action(methods=["post"], detail=True, permission_classes=[permissions.IsAdminUser])
    def refresh_uniprot(self, request, pk=None):
        project = self.get_object()
        accession_id = set()
        accession_map = {}
        for i in GeneNameMap.objects.filter(rawdata__file__project=project):
            for i2 in i.accession_id.split(";"):
                accession_id.add(i2)
                accession_map[i2] = i
        accession_id = list(accession_id)
        parser = UniprotParser()
        uni_df = []
        for p in parser.parse(accession_id):
            uniprot_df = pd.read_csv(io.StringIO(p), sep="\t")
            uni_df.append(uniprot_df)
        if len(uni_df) == 1:
            uni_df = uni_df[0]
        else:
            uni_df = pd.concat(uni_df, ignore_index=True)
        uniprot_record_map = {}
        with transaction.atomic():
            for ind, row in uni_df.iterrows():
                uniprot_record = UniprotRecord.objects.filter(entry=row["Entry"]).first()
                if uniprot_record:
                    uniprot_record.record = json.dumps(row.to_dict())
                else:
                    uniprot_record = UniprotRecord(entry=row["Entry"], record=json.dumps(row.to_dict()))
                uniprot_record.save()
                uniprot_record_map[uniprot_record.entry] = uniprot_record
            for ind, row in uni_df.iterrows():
                if row["From"] in accession_map:
                    accession_map[row["From"]].entry = row["Entry"]
                    if row["Entry"] in uniprot_record_map:
                        accession_map[row["From"]].uniprot_record = uniprot_record_map[row["Entry"]]
                    if pd.notnull(row["Gene Names"]):
                        accession_map[row["From"]].gene_names = row["Gene Names"].upper()
                    else:
                        accession_map[row["From"]].gene_names = row["Entry"]
                    accession_map[row["From"]].save()

class AuthorViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema


class KeywordViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = Keyword.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = KeywordSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "name", "project_count")
    ordering = ("name",)
    filter_mappings = {
        "id": "id",
        "name": "name__icontains"
    }
    filter_validation_schema = organism_query_schema


class ComparisonViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = Comparison.objects.all()
    serializer_class = ComparisonSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [filters.OrderingFilter]
    permit_list_expands = ["file", "file.project"]
    ordering_fields = ("id", "name", "file_id")
    ordering = ("file_id", "name")
    filter_mappings = {
        "id": "id",
        "name": "name__icontains",
        "file_id": "file_id__exact"
    }
    filter_validation_schema = comparison_query_schema

    #def get_object(self):
        #return get_object_or_404(Comparison, id=self.kwargs['pk'])

    def get_queryset(self):
        if is_expanded(self.request, 'file'):
            self.queryset = self.queryset.select_related('file')
        if is_expanded(self.request, 'file.project'):
            self.queryset = self.queryset.select_related('file__project')
        return self.queryset.distinct()


class FileViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    parser_classes = [MultiPartParser]
    permit_list_expands = ["project"]

    def get_queryset(self):
        is_staff = is_user_staff(self.request)
        if is_expanded(self.request, 'project'):
            self.queryset = self.queryset.select_related('project')

        #ptm_data = self.request.query_params.get("ptm_data")

        #if ptm_data:
            #self.queryset = self.queryset.filter(ptm_data=ptm_data)
        if is_staff:
            return self.queryset.distinct()

        project_limit = Project.objects.filter(enable=True)
        return self.queryset.filter(project__in=project_limit).distinct()

    def create(self, request, **kwargs):
        file = File()
        print(self.request.data)
        filename = self.request.data["file"].name.split('.')[:-1]
        file.file.save(f"{filename}.{uuid.uuid4()}.txt", djangoFile(self.request.data["file"]))
        file.file_type = self.request.data["file_type"]
        file.save()
        file_json = FileSerializer(file, many=False, context={"request": request})
        print(file_json.data)
        return Response(data=file_json.data)

    @method_decorator(cache_page(60 * 60 * 2))
    @action(methods=["get"], detail=True)
    def get_columns(self, request, pk=None):
        file = self.get_object()
        columns = []
        print(file)
        print(file.file)
        with open(file.file.path, "rt") as f:
            for line in f:
                line = line.strip()
                columns = line.split("\t")
                break
        return Response({"columns": columns})

    #@action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    # @action(methods=["post"], detail=True, permission_classes=[permissions.IsAuthenticated], parser_classes=[JSONParser])
    # def add_differential_analysis_data(self, request, pk=None):
    #     file = self.get_object()
    #     df = pd.read_csv(file.file.path, sep="\t")
    #     job_id = async_task('celsus.utils.process_differential_analysis_data', self.request.data, file, df)
    #     #file_json = FileSerializer(file, context={'request': request})
    #     #file_json.data["id"] = file.id
    #     return Response(data={'job_id': job_id})
    #
    #
    #
    # @action(methods=["post"], detail=True, permission_classes=[permissions.IsAuthenticated], parser_classes=[JSONParser])
    # def add_raw_data(self, request, pk=None):
    #
    #     file = self.get_object()
    #     df = pd.read_csv(file.file.path, sep="\t")
    #     job_id = async_task('celsus.utils.process_raw_data', self.request.data, file, df)
    #
    #     return Response(data={'job_id': job_id})

    def update(self, request, *args, **kwargs):
        file = self.get_object()
        if file.project.id != self.request.data["project"]["id"]:
            project = Project.objects.filter(pk=self.request.data["project"]["id"]).first()
            project.files.add(file)
            project.save()
            file.save()
        file_json = FileSerializer(file, context={'request': request})
        return Response(file_json.data)

    def destroy(self, request, *args, **kwargs):
        file = self.get_object()
        print("Deleting", file)
        delete_file_related_objects(file)
        file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(methods=["post"], detail=True, permission_classes=[permissions.IsAuthenticated], parser_classes=[JSONParser])
    def set_project(self, request, pk=None):
        file = self.get_object()
        if "project_id" in self.request.data:
            project = Project.objects.filter(pk=self.request.data["project_id"]).first()
            project.files.add(file)
            project.save()
            file.save()
        file_json = FileSerializer(file, context={'request': request})
        return Response(file_json.data)

    @action(methods=["get"], detail=True, permission_classes=[permissions.AllowAny])
    def get_project(self, request, pk=None):
        file = self.get_object()
        project_json = ProjectSerializer(file.project, context={'request': request})
        return Response(project_json.data)

    @action(methods=["get"], detail=True, permission_classes=[permissions.IsAdminUser | IsFileOwnerOrPublic,])
    def download(self, request, pk=None):
        file = self.get_object()
        _, file_name = os.path.split(file.file.name)
        return sendfile(request, file.file.name, attachment_filename=file_name)


class DifferentialSampleColumnViewSet(viewsets.ModelViewSet):
    queryset = DifferentialSampleColumn.objects.all()
    serializer_class = DifferentialSampleColumnSerializer


class LabGroupViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = LabGroup.objects.all().prefetch_related("project").annotate(project_count=Count("project"))
    serializer_class = LabGroupSerializer

class RawSampleColumnViewSet(viewsets.ModelViewSet):
    queryset = RawSampleColumn.objects.all()
    serializer_class = RawSampleColumnSerializer

    @method_decorator(cache_page(60 * 60 * 2))
    @action(methods=["get"], detail=True, permission_classes=[permissions.AllowAny])
    def get_boxplot_parameters(self, request, pk=None):
        raw_sample_column = self.get_object()
        data = RawData.objects.filter(raw_sample_column_id__exact=raw_sample_column.id)
        print(data.all())
        values = []
        for i in data.all():
            if i.value:
                values.append(np.log2(i.value))
        values = np.array(values)
        print(values)
        res = calculate_boxplot_parameters(values)
        res["id"] = raw_sample_column.id
        res["name"] = raw_sample_column.name
        return Response(res)


class DifferentialAnalysisDataViewSet(FiltersMixin, FlexFieldsMixin, viewsets.ModelViewSet):
    queryset = DifferentialAnalysisData.objects.all()
    serializer_class = DifferentialAnalysisDataSerializer
    filter_backends = [filters.OrderingFilter]
    permit_list_expands = ["gene_names", "comparison", "comparison.file", "comparison.file.project"]
    ordering_fields = ("id", "primary_id", "gene_names", "comparison", "fold_change", "significant")
    ordering = ("gene_names",)
    filter_mappings = {
        "id": "id",
        "primary_id": "primary_id__icontains",
        "gene_names": "gene_names__gene_names__icontains",
        "gene_names_exact": "gene_names__gene_names__exact",
        "primary_id_exact": "primary_id__exact",
        "comparison": "comparison_id__in",
        "ids": "pk__in",
        "ptm_data": "ptm_data",
    }
    filter_validation_schema = differential_data_query_schema

    def get_queryset(self):
        is_staff = is_user_staff(self.request)
        if is_expanded(self.request, 'comparison.file'):
            self.queryset = self.queryset.select_related('comparison__file')
        if is_expanded(self.request, 'comparison.file.project'):
            self.queryset = self.queryset.select_related('comparison__file__project')
        if is_expanded(self.request, 'comparison'):
            self.queryset = self.queryset.select_related('comparison')
        significant_cutoff = float(self.request.query_params.get("significant_cutoff", 0))
        fc_cutoff = abs(float(self.request.query_params.get("fc_cutoff", 0)))
        if significant_cutoff != 0:
            self.queryset = self.queryset.filter(significant__gte=float(significant_cutoff))
        if fc_cutoff != 0:
            query = Q()
            query.add(Q(fold_change__lte=-fc_cutoff), Q.OR)
            query.add(Q(fold_change__gte=fc_cutoff), Q.OR)
            self.queryset = self.queryset.filter(query)
        #ptm_data = self.request.query_params.get("ptm_data")

        #if ptm_data:
            #self.queryset = self.queryset.filter(ptm_data=ptm_data)

        if is_staff:
            return self.queryset.distinct()

        project_limit = Project.objects.filter(enable=True)
        return self.queryset.filter(comparison__file__project__in=project_limit).distinct()


    @action(methods=["post"], detail=False, permission_classes=[permissions.AllowAny])
    def search_gene(self, request, *args, **kwargs):
        results = []
        if len(self.request.data["query"]) > 0:
            if len(self.request.data["query"]) > 1:
                query = f"\s*({'|'.join(self.request.data['query'])})\s*"
            else:
                query = f"\s*{self.request.data['query'][0]}\s*"
            if self.request.data["query_type"] == "gene_names":
                results = DifferentialAnalysisData.objects.filter(gene_names__gene_names__iregex=query)
            elif self.request.data["query_type"] == "primary_id":
                results = DifferentialAnalysisData.objects.filter(primary_id__iregex=query.replace("\s", ";"))

        if len(results) > 1:
            if self.request.data["sort_by"]:
                results = results.order_by(self.request.data["sort_by"])
            else:
                results = results.order_by("fold_change")
            count = len(results)
            if self.request.data["offset"]:
                results = results[self.request.data["offset"]:]
            if len(results) > self.request.data["limit"]:
                results = results[:self.request.data["limit"]]

            result_json = DifferentialAnalysisDataSerializer(results, many=True, context={"request": request})
            return Response({
                "count": count,
                "results": result_json.data
            })
        return Response({"count": 0, "results": []})

class RawDataViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = RawData.objects.all()
    serializer_class = RawDataSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "primary_id", "gene_names")
    ordering = ("gene_names",)
    filter_mappings = {
        "id": "id",
        "primary_id": "primary_id__icontains",
        "gene_names": "gene_names__gene_names__icontains",
        "gene_names_exact": "gene_names__gene_names__exact",
        "accession_id": "gene_names__accession_id__icontains",
        "accession_id_exact": "gene_names__accession_id__exact",
        "primary_id_exact": "primary_id__exact",
        "file_id": "file_id__in",
        "ids": "pk__in"
    }

    filter_validation_schema = raw_data_query_schema

    def get_queryset(self):
        is_staff = is_user_staff(self.request)
        if is_staff:
            return self.queryset.distinct()
        project_limit = Project.objects.filter(enable=True)
        return RawData.objects.filter(file__project__in=project_limit).distinct()




class GeneNameMapViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = GeneNameMap.objects.all()
    serializer_class = GeneNameMapSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "accession_id", "gene_names")
    ordering = ("id", "gene_names",)
    filter_mappings = {
        "id": "id",
        "gene_names": "gene_names__icontains",
        "accession_id": "entry__icontains",
        "project": "rawdata__file__project_id__exact"
    }
    filter_validation_schema = gene_name_map_query_schema

    def get_queryset(self):
        if is_expanded(self.request, 'uniprot_record'):
            self.queryset = self.queryset.prefetch_related('uniprot_record')
        if is_expanded(self.request, 'primary_uniprot_record'):
            self.queryset = self.queryset.select_related('primary_uniprot_record')
        if self.request.user.is_staff:
            return self.queryset.distinct()
        project_limit = Project.objects.filter(enable=True)
        return self.queryset.filter(rawdata__file__project__in=project_limit).distinct()


class DataFilterListViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = DataFilterList.objects.all()
    serializer_class = DataFilterListSerializer
    filter_backends = [filters.OrderingFilter]
    permission_classes = [IsDataFilterListOwner|permissions.IsAuthenticatedOrReadOnly,]
    parser_classes = [MultiPartParser, JSONParser]
    ordering_fields = ("id", "name", "category")
    ordering = ("name", "category", "id")
    filter_mappings = {
        "id": "id",
        "name_exact": "name__exact",
        "category_exact": "category__exact",
    }
    filter_validation_schema = data_filter_list_query_schema

    def get_queryset(self):
        name = self.request.query_params.get("name", None)
        data = self.request.query_params.get("data", None)
        category = self.request.query_params.get("category", None)
        query = Q()
        if name:
            query.add(Q(name__icontains=name), Q.OR)
        if data:
            query.add(Q(data__icontains=data), Q.OR)
        if category:
            query.add(Q(category__icontains=category), Q.OR)
        result = self.queryset.filter(query)
        if self.request.user:
            if self.request.user.is_authenticated:
                query = Q()
                query.add(Q(default=True), Q.OR)
                query.add(Q(user=self.request.user), Q.OR)
                return result.filter(query).distinct()
        return result.filter(default=True).distinct()

    def create(self, request, *args, **kwargs):
        filter_list = DataFilterList(
            name=self.request.data["name"],
            data=self.request.data["data"],
            category="User's lists",
            user=self.request.user
        )

        filter_list.save()
        filter_data = DataFilterListSerializer(filter_list, many=False, context={"request": request})
        return Response(data=filter_data.data)

    def destroy(self, request, *args, **kwargs):
        filter_list = self.get_object()
        filter_list.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=False, permission_classes=[permissions.AllowAny])
    def get_all_category(self, request, *args, **kwargs):
        categories = DataFilterList.objects.values("category").distinct()
        #results = [i["category"] for i in categories if i["category"] != ""]
        results = [i["category"] for i in categories if i["category"] != ""]
        return Response(data=results, )


class CurtainViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = Curtain.objects.all()
    serializer_class = CurtainSerializer
    filter_backends = [filters.OrderingFilter]
    parser_classes = [MultiPartParser, JSONParser]
    permission_classes = [(permissions.IsAdminUser|IsNonUserPostAllow|IsCurtainOwnerOrPublic),]
    lookup_field = 'link_id'
    ordering_fields = ("id", "created")
    ordering = ("created", "id")
    filter_mappings = {
        "id": "id",
        "username": "owners__username",
        "description": "description__icontains",
        "curtain_type": "curtain_type__in"
    }
    filter_validation_schema = curtain_query_schema
    @action(methods=["get"], url_path="download/?token=(?P<token>[^/]*)", detail=True, permission_classes=[
        permissions.IsAdminUser | HasCurtainToken | IsCurtainOwnerOrPublic
    ])
    @method_decorator(cache_page(0))
    def download(self, request, pk=None, link_id=None, token=None):
        c = self.get_object()
        _, file_name = os.path.split(c.file.name)
        return sendfile(request, c.file.name, attachment_filename=file_name)

    @action(methods=["post"], detail=True, permission_classes=[permissions.IsAdminUser | IsCurtainOwner])
    def generate_token(self, request, pk=None, link_id=None):
        c = self.get_object()
        a = AccessToken()
        a.set_exp(lifetime=timedelta(days=self.request.data["lifetime"]))
        ca = CurtainAccessToken(token=str(a), curtain=c)
        ca.save()

        return Response(data={"link_id": c.link_id, "token": ca.token})

    def create(self, request, **kwargs):
        c = Curtain()
        c.file.save(str(c.link_id)+".json", djangoFile(self.request.data["file"]))
        if "description" in self.request.data:
            c.description = self.request.data["description"]
        if type(self.request.user) != AnonymousUser:
            c.owners.add(self.request.user)
        if "enable" in self.request.data:
            if self.request.data["enable"] == "True":
                c.enable = True
            else:
                c.enable = False
        if "curtain_type" in self.request.data:
            c.curtain_type = self.request.data["curtain_type"]
        c.save()
        curtain_json = CurtainSerializer(c, many=False, context={"request": request})
        if type(self.request.user) != AnonymousUser:
            if settings.CURTAIN_DEFAULT_USER_LINK_LIMIT != 0:
                total_count = self.request.user.curtain.count()
                self.request.user.extraproperties.curtain_link_limit_exceed = total_count >= settings.CURTAIN_DEFAULT_USER_LINK_LIMIT
            else:
                self.request.user.extraproperties.curtain_link_limit_exceed = False
            self.request.user.extraproperties.save()

        return Response(data=curtain_json.data)

    def update(self, request, *args, **kwargs):
        c = self.get_object()

        if "enable" in self.request.data:
            if self.request.data["enable"] == "True":
                c.enable = True
            else:
                c.enable = False

        if "file" in self.request.data:
            c.file.save(str(c.link_id) + ".json", djangoFile(self.request.data["file"]))
        if "description" in self.request.data:
            c.description = self.request.data["description"]
        c.save()
        curtain_json = CurtainSerializer(c, many=False, context={"request": request})
        return Response(data=curtain_json.data)

    @action(methods=["get"], detail=True, permission_classes=[
        permissions.IsAdminUser | IsCurtainOwner
    ])
    def get_ownership(self, request, pk=None, link_id=None):
        c = self.get_object()
        if self.request.user in c.owners.all():
            return Response(data={"link_id": c.link_id, "ownership": True})
        return Response(data={"link_id": c.link_id, "ownership": False})

    @action(methods=["get"], detail=True, permission_classes=[
        permissions.IsAdminUser | HasCurtainToken | IsCurtainOwner
    ])
    def get_owners(self, request, pk=None, link_id=None):
        c = self.get_object()
        owners = []
        for i in c.owners.all():
            owners.append({"id": i.id, "username": i.username})
        return Response(data={"link_id": link_id, "owners": owners})

    @action(methods=["patch"], detail=True, permission_classes=[
        permissions.IsAdminUser | IsCurtainOwner
    ])
    def add_owner(self, request, pk=None, link_id=None):
        c = self.get_object()
        if "username" in self.request.data:
            user = User.objects.filter(username=self.request.data["username"]).first()
            if user:
                if user not in c.owners.all():
                    c.owners.add(user)
                    c.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                user = User.objects.create_user(username=self.request.data["username"],
                                                password=User.objects.make_random_password())
                if user not in c.owners.all():
                    c.owners.add(user)
                    c.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["get"], detail=False, permission_classes=[permissions.IsAuthenticated])
    def get_curtain_list(self, request, pk=None, link_id=None):
        cs = self.request.user.curtain.all()
        cs_json = CurtainSerializer(cs, many=True, context={"request": request})
        return Response(data=cs_json.data)

    def destroy(self, request, *args, **kwargs):
        curtain = self.get_object()
        print("Deleting", curtain)
        curtain.delete()
        if settings.CURTAIN_DEFAULT_USER_LINK_LIMIT != 0:
            total_count = self.request.user.curtain.count()
            self.request.user.extraproperties.curtain_link_limit_exceed = total_count >= settings.CURTAIN_DEFAULT_USER_LINK_LIMIT
        else:
            self.request.user.extraproperties.curtain_link_limit_exceed = False
        self.request.user.extraproperties.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class KinaseLibraryViewSet(FiltersMixin, viewsets.ModelViewSet):
    queryset = KinaseLibraryModel.objects.all()
    serializer_class = KinaseLibrarySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("id", "entry")
    ordering = ("entry")
    filter_mappings = {
        "id": "id",
        "position": "position",
        "entry": "entry",
        "residue": "residue"
    }
    filter_validation_schema = kinase_library_query_schema


def update_section(section, data_array, model):
    section.clear()
    for ct in data_array:
        if "id" in ct:
            if ct["id"]:
                cell_type = model.objects.get(pk=ct["id"])
                section.add(cell_type)
            else:
                if "name" in ct:
                    cell_type = model.objects.filter(name__exact=ct["name"]).first()
                    if cell_type:
                        section.add(cell_type)
                #cell_type = model(**ct)
                #cell_type.save()
                #section.add(cell_type)
        else:
            if "name" in ct:
                cell_type = model.objects.filter(name__exact=ct["name"]).first()
                if cell_type:
                    section.add(cell_type)
                else:
                    cell_type = model(**ct)
                    cell_type.save()
                    section.add(cell_type)
            #cell_type = model(**ct)
            #cell_type.save()
            #section.add(cell_type)


