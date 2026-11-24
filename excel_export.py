"""Formatted Excel exporter using widely available openpyxl."""
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from extractor import FIELDS

DATE_FIELDS = {'Start Date', 'End Date', 'Cover Note Date'}

def create_workbook(items):
    wb = Workbook()
    summary = wb.active
    summary.title = 'Policy Summary'
    details = wb.create_sheet('Field Details')
    proposal = wb.create_sheet('Proposal Field Values')
    proposal.append(['Document','Section','Person','Field','Value','Page','Evidence'])
    headers = ['PDF', 'Pages'] + list(FIELDS)
    summary.append(headers)
    details.append(['Document','Field','Extracted Value','Page','Extraction Method','Source Evidence'])

    for name, result in items.items():
        if 'error' in result:
            continue
        for rec in result.get('proposal_records',[]):
            proposal.append([name,rec.get('Section',''),rec.get('Person',''),rec['Field'],
                             str(rec['Value']),rec['Page'],rec.get('Evidence','')])
        fields = result['fields']
        summary.append([name, result['page_count']] + [
            str(fields[f].get('value') or 'Not found') for f in FIELDS
        ])
        for field in FIELDS:
            info = fields[field]
            details.append([
                name, field, str(info.get('value') or 'Not found'),
                info.get('page') or '', info.get('method') or '',
                info.get('evidence') or ''
            ])

    navy = PatternFill('solid', fgColor='123047')
    alternate = PatternFill('solid', fgColor='F0F6FA')
    white_font = Font(name='Aptos', size=11, bold=True, color='FFFFFF')
    body_font = Font(name='Aptos', size=10, color='203447')
    for sheet in (summary, details, proposal):
        sheet.freeze_panes = 'C2' if sheet is summary else 'C2'
        sheet.sheet_view.showGridLines = False
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.print_options.horizontalCentered = True
        sheet.page_setup.orientation = 'landscape'
        sheet.page_setup.fitToWidth = 1
        sheet.row_dimensions[1].height = 38
        for cell in sheet[1]:
            cell.fill = navy
            cell.font = white_font
            cell.alignment = Alignment(vertical='center', wrap_text=True)
        for row in sheet.iter_rows(min_row=2):
            sheet.row_dimensions[row[0].row].height = 43
            for cell in row:
                cell.font = body_font
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if cell.row % 2 == 0:
                    cell.fill = alternate
                # Force text display (avoids Excel date interpretation / #####).
                if isinstance(cell.value, str):
                    cell.number_format = '@'
        if sheet.max_row > 1:
            end = f'{get_column_letter(sheet.max_column)}{sheet.max_row}'
            tbl = Table(displayName='PolicySummary' if sheet is summary else ('PolicyFieldDetails' if sheet is details else 'ProposalFields'), ref=f'A1:{end}')
            tbl.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2',showFirstColumn=False,showLastColumn=False,showRowStripes=False,showColumnStripes=False)
            sheet.add_table(tbl)
        sheet.auto_filter.ref = sheet.dimensions
        sheet.sheet_properties.outlinePr.summaryBelow = True

    summary.column_dimensions['A'].width = 36
    summary.column_dimensions['B'].width = 11
    for col, field in enumerate(FIELDS, start=3):
        letter = get_column_letter(col)
        width = 29
        if any(k in field.lower() for k in ('address', 'insured name', 'office name')):
            width = 56
        summary.column_dimensions[letter].width = width

    for i, w in enumerate([36, 28, 60, 12, 24, 85], start=1):
        details.column_dimensions[get_column_letter(i)].width = w

    for i,w in enumerate([36,27,19,37,57,12,75],start=1):
        proposal.column_dimensions[get_column_letter(i)].width=w
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
