package cing.client;

import com.google.gwt.user.client.History;
import com.google.gwt.user.client.ui.Button;
import com.google.gwt.user.client.ui.ClickListener;
import com.google.gwt.user.client.ui.DecoratorPanel;
import com.google.gwt.user.client.ui.HTML;
import com.google.gwt.user.client.ui.HasHorizontalAlignment;
import com.google.gwt.user.client.ui.HorizontalPanel;
import com.google.gwt.user.client.ui.Label;
import com.google.gwt.user.client.ui.Widget;

public class RunView extends iCingView {

	final HTML reportHTML = new HTML();
	DecoratorPanel decPanel = new DecoratorPanel();
	static final Button runButton = new Button();
	static final Button nextButton = new Button();
	iCingQuery cingQueryRun; 
	iCingConstants c = iCing.c;
	
	public RunView() {
		super();
	}
	
	public void setIcing(iCing icing) {
		super.setIcing(icing);
		final iCing icingShadow = icing;		
		setState(iCing.RUN_STATE);
		verticalPanel.add(decPanel);
		

		final Label html_1 = new Label( c.Run() );
		html_1.setStylePrimaryName("h1");
		verticalPanel.add(html_1);

		final Label html_2 = new Label( "Please press the button when you are ready." );
		verticalPanel.add(html_2);
		
		runButton.setText(c.Submit());
		runButton.addClickListener(new ClickListener() {
			public void onClick(final Widget sender) {
//				runButton.setText("Running...");
				run();
			}
		});
		runButton.setEnabled(true);
		
		verticalPanel.add(runButton);
		runButton.setTitle("Run the validation.");
		verticalPanel.setCellHorizontalAlignment(runButton, HasHorizontalAlignment.ALIGN_LEFT);
				
		
		
		nextButton.setText(c.Next());
		nextButton.addClickListener(new ClickListener() {
			public void onClick(final Widget sender) {
				icingShadow.onHistoryChanged(iCing.CING_LOG_STATE);					
			}
		});	
//		nextButton.setEnabled(false); //disable for testing it will be triggered by a run; or not...
		
		final HorizontalPanel horizontalPanelBackNext = new HorizontalPanel();
		horizontalPanelBackNext.setSpacing(iCing.margin);
		verticalPanel.add(horizontalPanelBackNext);
		final Button backButton = new Button();
		horizontalPanelBackNext.add(backButton);
		backButton.addClickListener(new ClickListener() {
			public void onClick(final Widget sender) {
				History.back();
			}
		});
		backButton.setText(c.Back());
		horizontalPanelBackNext.add(backButton);
		horizontalPanelBackNext.add(nextButton);
		
		nextButton.setTitle("Goto CING log.");
//		verticalPanel.setCellHorizontalAlignment(nextButton, HasHorizontalAlignment.ALIGN_CENTER);
//		nextButton.setVisible(false);
		cingQueryRun = new iCingQuery(icing); 
		cingQueryRun.action.setValue(Keys.FORM_ACTION_RUN);
		verticalPanel.add(cingQueryRun.formPanel);
		
	}	
	
	protected void run() {		
		runButton.setEnabled(false);
		nextButton.setEnabled(true); 
		icing.cingLogView.getProjectName();		
		cingQueryRun.formPanel.submit();		
		icing.onHistoryChanged(iCing.CING_LOG_STATE);							
	}			
}
